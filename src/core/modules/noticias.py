"""Modulo de noticias com descoberta automatica de feeds.

Este modulo integra:
- ``findfeed`` para localizar URLs RSS/Atom a partir de um site.
- ``reader`` para armazenar, atualizar e ler itens dos feeds.
"""

from __future__ import annotations

from datetime import datetime
from email.message import Message
import html
import json
import logging
from pathlib import Path
import re
import sys
import types
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urljoin, urlparse, urlunparse

try:
    from core.config.settings import settings
except Exception:
    try:
        from ...config.settings import settings
    except Exception:
        settings = None

def _ensure_cgi_compat() -> None:
    """Compatibilidade para bibliotecas antigas que dependem de cgi.parse_header."""
    if "cgi" in sys.modules:
        return
    try:
        import cgi  # type: ignore  # pragma: no cover
        _ = cgi
        return
    except Exception:
        pass

    compat_module = types.ModuleType("cgi")

    def parse_header(line: str):
        value = str(line or "").strip()
        if not value:
            return "", {}
        message = Message()
        message["content-type"] = value
        params = message.get_params(header="content-type", unquote=True) or []
        if not params:
            ctype = value.split(";", 1)[0].strip()
            return ctype, {}
        ctype = str(params[0][0] or "").strip()
        pdict: Dict[str, str] = {}
        for key, val in params[1:]:
            pdict[str(key)] = "" if val is None else str(val)
        return ctype, pdict

    compat_module.parse_header = parse_header  # type: ignore[attr-defined]
    sys.modules["cgi"] = compat_module


_ensure_cgi_compat()

try:
    import findfeed  # type: ignore
    _FINDFEED_IMPORT_ERROR = ""
except Exception as exc:
    findfeed = None
    _FINDFEED_IMPORT_ERROR = str(exc)

try:
    from reader import make_reader  # type: ignore
    _READER_IMPORT_ERROR = ""
except Exception as exc:
    make_reader = None
    _READER_IMPORT_ERROR = str(exc)

logger = logging.getLogger(__name__)


class NoticiasModule:
    """Gerencia descoberta e leitura de noticias via RSS/Atom."""

    DEFAULT_DB_RELATIVE_PATH = Path("06-RECURSOS") / "noticias" / "news_reader.sqlite"
    DEFAULT_FEED_LIMITS_RELATIVE_PATH = Path("06-RECURSOS") / "noticias" / "feed_limits.json"
    DEFAULT_DAILY_LIMIT_PER_FEED = 10

    def __init__(self, vault_path: str | Path | None = None, db_path: str | Path | None = None):
        self.vault_path = self._resolve_vault_path(vault_path)
        self.db_path = self._resolve_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.feed_limits_path = self._resolve_feed_limits_path()
        self.feed_limits_path.parent.mkdir(parents=True, exist_ok=True)
        self._reader = None

    def dependency_status(self) -> Dict[str, Any]:
        """Retorna o status das dependencias opcionais do modulo."""
        return {
            "reader_available": make_reader is not None,
            "findfeed_available": findfeed is not None,
            "reader_import_error": _READER_IMPORT_ERROR,
            "findfeed_import_error": _FINDFEED_IMPORT_ERROR,
            "db_path": str(self.db_path),
        }

    def discover_feeds(self, source_url: str, max_results: int = 10) -> List[str]:
        """Descobre feeds RSS/Atom de um site usando ``findfeed``."""
        if findfeed is None:
            detail = _FINDFEED_IMPORT_ERROR or "motivo de importacao nao informado"
            logger.error("findfeed indisponivel para descoberta de feeds: %s", detail)
            raise RuntimeError(f"Dependencia ausente: instale 'findfeed' para descoberta de feeds. Detalhe: {detail}")

        normalized_source = self._normalize_url(source_url)
        discovered_payload = self._call_findfeed(normalized_source)
        candidates = self._extract_urls(discovered_payload)
        if self._looks_like_feed_url(normalized_source):
            candidates.insert(0, normalized_source)

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                normalized = self._normalize_url(candidate)
            except Exception:
                continue
            key = self._url_sort_key(normalized)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
            if len(deduped) >= max(1, int(max_results)):
                break
        return deduped

    def add_feed(self, feed_url: str, *, update: bool = True) -> Dict[str, Any]:
        """Adiciona um feed no banco do reader e opcionalmente atualiza."""
        normalized_feed = self._normalize_url(feed_url)
        reader_client = self._get_reader()

        added = False
        try:
            self._reader_add_feed(reader_client, normalized_feed)
            added = True
        except Exception as exc:
            if not self._is_duplicate_feed_error(exc):
                return {
                    "ok": False,
                    "feed_url": normalized_feed,
                    "added": False,
                    "updated": False,
                    "error": str(exc),
                }

        updated = False
        update_error = ""
        if update:
            try:
                self._reader_update_single(reader_client, normalized_feed)
                updated = True
            except Exception as exc:
                update_error = str(exc)
                if self._is_non_feed_parse_error(exc):
                    if added:
                        self._reader_delete_feed(reader_client, normalized_feed)
                    return {
                        "ok": False,
                        "feed_url": normalized_feed,
                        "added": False,
                        "updated": False,
                        "error": (
                            "URL informada nao parece ser um feed RSS/Atom valido. "
                            "Use descoberta automatica por site."
                        ),
                    }
                logger.warning("Falha ao atualizar feed '%s': %s", normalized_feed, exc)

        return {
            "ok": True,
            "feed_url": normalized_feed,
            "added": added,
            "updated": updated,
            "error": update_error,
        }

    def add_from_input(
        self,
        source_or_feed_url: str,
        *,
        update: bool = True,
        max_discovered: int = 10,
        max_subscriptions: int = 5,
    ) -> Dict[str, Any]:
        """Adiciona um feed direto ou descobre feeds automaticamente a partir de um site."""
        normalized = self._normalize_url(source_or_feed_url)
        if self._looks_like_feed_url(normalized):
            result = self.add_feed(normalized, update=update)
            return {
                "ok": bool(result.get("ok")),
                "mode": "feed",
                "source_url": normalized,
                "discovered_count": 0,
                "subscribed_count": 1 if bool(result.get("ok")) else 0,
                "feeds": [result],
            }

        discovered_result: Dict[str, Any]
        try:
            discovered_result = self.subscribe_from_source(
                normalized,
                max_discovered=max_discovered,
                max_subscriptions=max_subscriptions,
                update=update,
            )
        except Exception as exc:
            discovered_result = {
                "source_url": normalized,
                "discovered_count": 0,
                "subscribed_count": 0,
                "feeds": [],
                "error": str(exc),
            }
        subscribed_count = int(discovered_result.get("subscribed_count", 0) or 0)
        if subscribed_count > 0:
            return {
                "ok": True,
                "mode": "source",
                "source_url": normalized,
                "discovered_count": int(discovered_result.get("discovered_count", 0) or 0),
                "subscribed_count": subscribed_count,
                "feeds": list(discovered_result.get("feeds") or []),
            }

        # Fallback: tenta como feed direto caso a URL nao tenha marcador explícito.
        fallback = self.add_feed(normalized, update=update)
        return {
            "ok": bool(fallback.get("ok")),
            "mode": "fallback",
            "source_url": normalized,
            "discovered_count": int(discovered_result.get("discovered_count", 0) or 0),
            "subscribed_count": 1 if bool(fallback.get("ok")) else 0,
            "feeds": [fallback],
        }

    def subscribe_from_source(
        self,
        source_url: str,
        *,
        max_discovered: int = 10,
        max_subscriptions: int = 5,
        update: bool = True,
    ) -> Dict[str, Any]:
        """Descobre feeds de uma fonte e assina automaticamente os melhores candidatos."""
        discovered = self.discover_feeds(source_url, max_results=max_discovered)
        selected = sorted(
            discovered,
            key=lambda candidate: self._feed_subscription_priority(candidate, source_url),
        )[: max(1, int(max_subscriptions))]

        results: List[Dict[str, Any]] = []
        for feed_url in selected:
            results.append(self.add_feed(feed_url, update=update))

        return {
            "source_url": self._normalize_url(source_url),
            "discovered_count": len(discovered),
            "subscribed_count": sum(1 for result in results if result.get("ok")),
            "feeds": results,
        }

    def _feed_subscription_priority(self, feed_url: str, source_url: str) -> tuple[int, int, int, str]:
        """Ordena candidatos de feed priorizando notícias no mesmo domínio e evitando podcasts."""
        try:
            normalized_feed = self._normalize_url(feed_url)
            normalized_source = self._normalize_url(source_url)
        except Exception:
            lowered = str(feed_url or "").strip().lower()
            is_podcast = 1 if "podcast" in lowered else 0
            return (is_podcast, 1, 1, lowered)

        feed_parsed = urlparse(normalized_feed)
        source_parsed = urlparse(normalized_source)
        feed_host = str(feed_parsed.netloc or "").strip().lower()
        source_host = str(source_parsed.netloc or "").strip().lower()

        def _strip_www(host: str) -> str:
            return host[4:] if host.startswith("www.") else host

        feed_host_base = _strip_www(feed_host)
        source_host_base = _strip_www(source_host)
        same_domain = (
            0
            if (
                feed_host_base == source_host_base
                or feed_host_base.endswith("." + source_host_base)
                or source_host_base.endswith("." + feed_host_base)
            )
            else 1
        )

        lowered = normalized_feed.lower()
        is_podcast = 1 if any(marker in lowered for marker in ("podcast", "omnycontent")) else 0
        has_feed_marker = 0 if self._looks_like_feed_url(normalized_feed) else 1
        return (is_podcast, same_domain, has_feed_marker, lowered)

    def update_feeds(self, feed_urls: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Atualiza todos os feeds ou uma lista especifica."""
        reader_client = self._get_reader()

        if not feed_urls:
            self._reader_update_all(reader_client)
            return {"ok": True, "updated_feeds": "all"}

        normalized = [self._normalize_url(url) for url in feed_urls if str(url or "").strip()]
        updated = 0
        errors: List[Dict[str, str]] = []
        for feed_url in normalized:
            try:
                self._reader_update_single(reader_client, feed_url)
                updated += 1
            except Exception as exc:
                errors.append({"feed_url": feed_url, "error": str(exc)})

        return {
            "ok": len(errors) == 0,
            "updated_feeds": updated,
            "errors": errors,
        }

    def list_feeds(self) -> List[Dict[str, Any]]:
        """Lista feeds cadastrados no banco do reader."""
        reader_client = self._get_reader()
        get_feeds = getattr(reader_client, "get_feeds", None)
        if not callable(get_feeds):
            raise RuntimeError("Objeto reader nao expoe metodo 'get_feeds'.")

        feeds: List[Dict[str, Any]] = []
        for feed in get_feeds():
            feed_url = self._coalesce_attr(feed, "url", "feed_url")
            if not feed_url:
                continue
            feeds.append(
                {
                    "url": str(feed_url),
                    "title": self._coalesce_attr(feed, "title", default=""),
                    "updated": self._to_iso(self._coalesce_attr(feed, "updated")),
                    "last_updated": self._to_iso(self._coalesce_attr(feed, "last_updated")),
                }
            )
        return feeds

    def remove_feed(self, feed_url: str) -> Dict[str, Any]:
        """Remove um feed cadastrado."""
        normalized_feed = self._normalize_url(feed_url)
        reader_client = self._get_reader()
        try:
            self._reader_delete_feed(reader_client, normalized_feed)
            self._remove_feed_limit(normalized_feed)
            return {"ok": True, "feed_url": normalized_feed}
        except Exception as exc:
            return {"ok": False, "feed_url": normalized_feed, "error": str(exc)}

    def set_feed_daily_limit(self, feed_url: str, daily_limit: int) -> Dict[str, Any]:
        normalized_feed = self._normalize_url(feed_url)
        bounded_limit = max(1, min(200, int(daily_limit)))
        data = self._load_feed_limits()
        key = self._url_sort_key(normalized_feed)
        data[key] = {"feed_url": normalized_feed, "daily_limit": bounded_limit}
        self._save_feed_limits(data)
        return {"ok": True, "feed_url": normalized_feed, "daily_limit": bounded_limit}

    def get_feed_daily_limit(self, feed_url: str) -> int:
        normalized_feed = self._normalize_url(feed_url)
        data = self._load_feed_limits()
        key = self._url_sort_key(normalized_feed)
        payload = data.get(key)
        if isinstance(payload, dict):
            try:
                return max(1, int(payload.get("daily_limit", self.DEFAULT_DAILY_LIMIT_PER_FEED)))
            except Exception:
                return self.DEFAULT_DAILY_LIMIT_PER_FEED
        if isinstance(payload, int):
            return max(1, int(payload))
        return self.DEFAULT_DAILY_LIMIT_PER_FEED

    def list_feeds_with_daily_counts(self) -> List[Dict[str, Any]]:
        """Lista feeds com contagem de itens publicados hoje (horário local)."""
        feeds = self.list_feeds()
        if not feeds:
            return []

        today = datetime.now().date()
        reader_client = self._get_reader()
        enriched: List[Dict[str, Any]] = []

        for feed in feeds:
            feed_url = str(feed.get("url") or "").strip()
            if not feed_url:
                continue
            daily_count = 0
            try:
                entries_iter = self._reader_get_entries(reader_client, feed_url=feed_url)
                for entry in entries_iter:
                    published = self._coalesce_attr(entry, "published", "updated")
                    parsed = self._parse_entry_datetime(published)
                    if parsed is None:
                        continue
                    if parsed.date() == today:
                        daily_count += 1
            except Exception:
                daily_count = 0

            merged = dict(feed)
            merged["daily_count"] = int(daily_count)
            merged["daily_limit"] = int(self.get_feed_daily_limit(feed_url))
            enriched.append(merged)
        return enriched

    def latest_entries(
        self,
        *,
        limit: int = 20,
        feed_url: Optional[str] = None,
        update_before_read: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retorna as entradas mais recentes, com filtro opcional de feed."""
        if update_before_read:
            self.update_feeds([feed_url] if feed_url else None)

        reader_client = self._get_reader()
        normalized_filter = self._normalize_url(feed_url) if feed_url else ""
        entries_iter = self._reader_get_entries(reader_client, feed_url=normalized_filter or None)
        today = datetime.now().date()
        per_feed_limits = self._load_feed_limits()
        per_feed_count: Dict[str, int] = {}
        resolved_limits: Dict[str, int] = {}

        entries: List[Dict[str, Any]] = []
        for entry in entries_iter:
            entry_feed_url = self._entry_feed_url(entry)
            if normalized_filter and self._url_sort_key(entry_feed_url) != self._url_sort_key(normalized_filter):
                continue

            published_obj = self._coalesce_attr(entry, "published", "updated")
            published_dt = self._parse_entry_datetime(published_obj)
            if published_dt is None or published_dt.date() != today:
                continue

            feed_key = self._url_sort_key(entry_feed_url)
            if feed_key not in resolved_limits:
                limit_payload = per_feed_limits.get(feed_key)
                if isinstance(limit_payload, dict):
                    try:
                        resolved_limits[feed_key] = max(
                            1,
                            int(limit_payload.get("daily_limit", self.DEFAULT_DAILY_LIMIT_PER_FEED)),
                        )
                    except Exception:
                        resolved_limits[feed_key] = self.DEFAULT_DAILY_LIMIT_PER_FEED
                elif isinstance(limit_payload, int):
                    resolved_limits[feed_key] = max(1, int(limit_payload))
                else:
                    resolved_limits[feed_key] = self.DEFAULT_DAILY_LIMIT_PER_FEED

            current_limit = int(resolved_limits.get(feed_key, self.DEFAULT_DAILY_LIMIT_PER_FEED))
            already_added = int(per_feed_count.get(feed_key, 0))
            if already_added >= current_limit:
                continue

            entries.append(
                {
                    "feed_url": entry_feed_url,
                    "entry_id": self._coalesce_attr(entry, "id", "entry_id", default=""),
                    "title": self._coalesce_attr(entry, "title", default="(sem titulo)"),
                    "url": self._coalesce_attr(entry, "link", "url", default=""),
                    "summary": self._entry_summary(entry),
                    "subtitle": self._entry_subtitle(entry),
                    "source": self._entry_source(entry),
                    "cover_url": self._entry_cover_url(entry),
                    "published": self._to_iso(published_obj),
                    "updated": self._to_iso(self._coalesce_attr(entry, "updated")),
                }
            )
            per_feed_count[feed_key] = already_added + 1
            if len(entries) >= max(1, int(limit)):
                break
        return entries

    def _resolve_vault_path(self, vault_path: str | Path | None) -> Optional[Path]:
        if vault_path:
            return Path(vault_path).expanduser().resolve(strict=False)

        try:
            configured = str(getattr(getattr(settings, "paths", None), "vault", "") or "").strip()
            if configured:
                return Path(configured).expanduser().resolve(strict=False)
        except Exception:
            pass
        return None

    def _resolve_db_path(self, db_path: str | Path | None) -> Path:
        if db_path:
            return Path(db_path).expanduser().resolve(strict=False)
        if self.vault_path is not None:
            return (self.vault_path / self.DEFAULT_DB_RELATIVE_PATH).resolve(strict=False)
        return (Path.cwd() / "data" / "noticias" / "news_reader.sqlite").resolve(strict=False)

    def _resolve_feed_limits_path(self) -> Path:
        if self.vault_path is not None:
            return (self.vault_path / self.DEFAULT_FEED_LIMITS_RELATIVE_PATH).resolve(strict=False)
        return self.db_path.with_name("feed_limits.json")

    def _load_feed_limits(self) -> Dict[str, Any]:
        path = self.feed_limits_path
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}

    def _save_feed_limits(self, payload: Dict[str, Any]) -> None:
        self.feed_limits_path.parent.mkdir(parents=True, exist_ok=True)
        self.feed_limits_path.write_text(
            json.dumps(payload or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _remove_feed_limit(self, feed_url: str) -> None:
        normalized_feed = self._normalize_url(feed_url)
        key = self._url_sort_key(normalized_feed)
        data = self._load_feed_limits()
        if key in data:
            data.pop(key, None)
            self._save_feed_limits(data)

    def _get_reader(self):
        if make_reader is None:
            detail = _READER_IMPORT_ERROR or "motivo de importacao nao informado"
            logger.error("reader indisponivel para modulo de noticias: %s", detail)
            raise RuntimeError(f"Dependencia ausente: instale 'reader' para usar o modulo de noticias. Detalhe: {detail}")
        if self._reader is None:
            self._reader = make_reader(str(self.db_path))
        return self._reader

    def _call_findfeed(self, source_url: str) -> Any:
        assert findfeed is not None  # protegido em discover_feeds()
        last_error: Optional[Exception] = None

        for func_name in ("find_feeds", "findfeeds", "search", "find"):
            func = getattr(findfeed, func_name, None)
            if not callable(func):
                continue

            for args, kwargs in (((source_url,), {}), ((), {"url": source_url})):
                try:
                    return func(*args, **kwargs)
                except TypeError:
                    continue
                except Exception as exc:
                    last_error = exc
                    break

        finder_cls = getattr(findfeed, "Finder", None)
        if callable(finder_cls):
            finder = finder_cls()
            for method_name in ("find", "find_feeds", "search"):
                method = getattr(finder, method_name, None)
                if not callable(method):
                    continue
                try:
                    return method(source_url)
                except Exception as exc:
                    last_error = exc

        if last_error is not None:
            raise RuntimeError(f"Falha ao descobrir feeds via findfeed: {last_error}") from last_error
        raise RuntimeError("API compativel do findfeed nao encontrada.")

    @staticmethod
    def _extract_urls(payload: Any) -> List[str]:
        if payload is None:
            return []
        direct = NoticiasModule._to_url_candidate(payload)
        if direct:
            return [direct]

        if isinstance(payload, dict):
            urls: List[str] = []
            for key in ("feeds", "urls", "results", "items", "data"):
                value = payload.get(key)
                urls.extend(NoticiasModule._extract_urls(value))
            if not urls:
                for key in ("url", "feed", "href", "feed_url"):
                    value = payload.get(key)
                    candidate = NoticiasModule._to_url_candidate(value)
                    if candidate:
                        urls.append(candidate)
            return urls

        if isinstance(payload, Iterable):
            urls: List[str] = []
            for item in payload:
                candidate = NoticiasModule._to_url_candidate(item)
                if candidate:
                    urls.append(candidate)
                    continue
                if isinstance(item, dict):
                    urls.extend(NoticiasModule._extract_urls(item))
                    continue
                url_value = NoticiasModule._coalesce_attr(item, "url", "href", "feed_url", "feed", default="")
                candidate = NoticiasModule._to_url_candidate(url_value)
                if candidate:
                    urls.append(candidate)
            return urls
        return []

    @staticmethod
    def _to_url_candidate(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.lower().startswith(("http://", "https://")):
            return text
        return ""

    @staticmethod
    def _normalize_url(url: str) -> str:
        value = str(url or "").strip()
        if not value:
            raise ValueError("URL vazia.")
        parsed = urlparse(value)
        if not parsed.scheme:
            parsed = urlparse(f"https://{value}")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"URL invalida: {value}")
        path = parsed.path or "/"
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))

    @staticmethod
    def _url_sort_key(url: str) -> str:
        try:
            normalized = NoticiasModule._normalize_url(url)
        except Exception:
            return str(url or "").strip().lower()
        parsed = urlparse(normalized)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{parsed.query}".lower()

    @staticmethod
    def _looks_like_feed_url(url: str) -> bool:
        lowered = str(url or "").strip().lower()
        markers = ("/feed", "rss", "atom", ".xml")
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _coalesce_attr(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            value = getattr(obj, name, None)
            if value is not None:
                return value
        return default

    @staticmethod
    def _to_iso(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _parse_entry_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                try:
                    return value.astimezone()
                except Exception:
                    return value
            return value

        raw = str(value or "").strip()
        if not raw:
            return None
        candidates = (raw, raw.replace("Z", "+00:00"), raw.split("T", 1)[0])
        for candidate in candidates:
            try:
                parsed = datetime.fromisoformat(candidate)
                if parsed.tzinfo is not None:
                    try:
                        parsed = parsed.astimezone()
                    except Exception:
                        pass
                return parsed
            except Exception:
                continue
        return None

    @staticmethod
    def _is_duplicate_feed_error(exc: Exception) -> bool:
        text = str(exc or "").lower()
        markers = ("already exists", "exists", "duplicate", "integrityerror", "unique constraint")
        return any(marker in text for marker in markers)

    @staticmethod
    def _is_non_feed_parse_error(exc: Exception) -> bool:
        text = str(exc or "").lower()
        markers = (
            "error while parsing feed",
            "saxparseexception",
            "xml",
            "not well-formed",
            "mismatched tag",
            "syntax error",
            "content is not allowed in prolog",
        )
        return any(marker in text for marker in markers)

    def _reader_add_feed(self, reader_client: Any, feed_url: str) -> None:
        add_feed = getattr(reader_client, "add_feed", None)
        if not callable(add_feed):
            raise RuntimeError("Objeto reader nao expoe metodo 'add_feed'.")
        try:
            add_feed(feed_url)
            return
        except TypeError:
            add_feed(url=feed_url)

    def _reader_update_all(self, reader_client: Any) -> None:
        update_feeds = getattr(reader_client, "update_feeds", None)
        if not callable(update_feeds):
            raise RuntimeError("Objeto reader nao expoe metodo 'update_feeds'.")
        update_feeds()

    def _reader_update_single(self, reader_client: Any, feed_url: str) -> None:
        update_feed = getattr(reader_client, "update_feed", None)
        if callable(update_feed):
            try:
                update_feed(feed_url)
                return
            except TypeError:
                update_feed(url=feed_url)
                return

        update_feeds = getattr(reader_client, "update_feeds", None)
        if not callable(update_feeds):
            raise RuntimeError("Objeto reader nao expoe metodos de atualizacao de feed.")

        for args, kwargs in (
            (([feed_url],), {}),
            ((feed_url,), {}),
            ((), {"feed": feed_url}),
            ((), {"url": feed_url}),
        ):
            try:
                update_feeds(*args, **kwargs)
                return
            except TypeError:
                continue
        update_feeds()

    def _reader_delete_feed(self, reader_client: Any, feed_url: str) -> None:
        for method_name in ("delete_feed", "remove_feed"):
            method = getattr(reader_client, method_name, None)
            if not callable(method):
                continue
            for args, kwargs in (((feed_url,), {}), ((), {"url": feed_url})):
                try:
                    method(*args, **kwargs)
                    return
                except TypeError:
                    continue
                except Exception:
                    return

    def _reader_get_entries(self, reader_client: Any, feed_url: Optional[str] = None):
        get_entries = getattr(reader_client, "get_entries", None)
        if not callable(get_entries):
            raise RuntimeError("Objeto reader nao expoe metodo 'get_entries'.")

        if not feed_url:
            return get_entries()

        for kwargs in ({"feed": feed_url}, {"feed_url": feed_url}, {"url": feed_url}):
            try:
                return get_entries(**kwargs)
            except TypeError:
                continue
        return get_entries()

    def _entry_feed_url(self, entry: Any) -> str:
        direct = self._coalesce_attr(entry, "feed_url", default="")
        if isinstance(direct, str) and direct:
            return direct
        feed_obj = self._coalesce_attr(entry, "feed", default=None)
        if feed_obj is not None:
            feed_url = self._coalesce_attr(feed_obj, "url", "feed_url", default="")
            if isinstance(feed_url, str):
                return feed_url
        resource_id = self._coalesce_attr(entry, "resource_id", default=None)
        if isinstance(resource_id, (tuple, list)) and resource_id:
            return str(resource_id[0] or "")
        return ""

    def _entry_summary(self, entry: Any) -> str:
        summary = self._coalesce_attr(entry, "summary", "content", "description", default="")
        if isinstance(summary, str):
            return summary
        if isinstance(summary, list) and summary:
            first = summary[0]
            if isinstance(first, dict):
                return str(first.get("value") or "")
            return str(first or "")
        if isinstance(summary, dict):
            return str(summary.get("value") or summary.get("content") or "")
        return str(summary or "")

    def _entry_subtitle(self, entry: Any, max_chars: int = 180) -> str:
        summary = self._entry_summary(entry)
        plain = self._html_to_plain(summary)
        if not plain:
            return ""
        if len(plain) <= max_chars:
            return plain
        return plain[: max(40, int(max_chars) - 1)].rstrip() + "..."

    def _entry_source(self, entry: Any) -> str:
        feed_obj = self._coalesce_attr(entry, "feed", default=None)
        if feed_obj is not None:
            title = self._coalesce_attr(feed_obj, "title", default="")
            if title:
                return str(title)
        return self._entry_feed_url(entry)

    def _entry_cover_url(self, entry: Any) -> str:
        base_url = str(self._coalesce_attr(entry, "link", "url", default="") or "").strip()
        direct = self._coalesce_attr(
            entry,
            "cover_url",
            "image_url",
            "image",
            "thumbnail",
            default="",
        )
        direct_candidate = self._normalize_cover_url(direct, base_url=base_url)
        if direct_candidate:
            return direct_candidate

        for attr_name in ("enclosures", "media_content", "links"):
            candidates = self._coalesce_attr(entry, attr_name, default=None)
            extracted = self._extract_image_url_from_iterable(candidates, base_url=base_url)
            if extracted:
                return extracted

        summary = self._entry_summary(entry)
        from_summary = self._extract_first_image_from_html(summary, base_url=base_url)
        if from_summary:
            return from_summary
        return ""

    @staticmethod
    def _extract_image_url_from_iterable(value: Any, base_url: str = "") -> str:
        if value is None or isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
            return ""
        for item in value:
            if isinstance(item, str):
                candidate = NoticiasModule._normalize_cover_url(item, base_url=base_url)
                if candidate and NoticiasModule._looks_like_image_url(candidate):
                    return candidate
                continue

            if isinstance(item, dict):
                candidate = NoticiasModule._normalize_cover_url(
                    item.get("href") or item.get("url") or "",
                    base_url=base_url,
                )
                media_type = str(item.get("type") or "").strip().lower()
                if candidate and (
                    media_type.startswith("image/")
                    or NoticiasModule._looks_like_image_url(candidate)
                ):
                    return candidate
                continue

            candidate = NoticiasModule._normalize_cover_url(
                NoticiasModule._coalesce_attr(item, "href", "url", default=""),
                base_url=base_url,
            )
            media_type = str(NoticiasModule._coalesce_attr(item, "type", default="") or "").strip().lower()
            if candidate and (
                media_type.startswith("image/")
                or NoticiasModule._looks_like_image_url(candidate)
            ):
                return candidate
        return ""

    @staticmethod
    def _extract_first_image_from_html(value: str, base_url: str = "") -> str:
        text = str(value or "")
        if not text:
            return ""
        match = re.search(r"""<img[^>]+src=["']([^"']+)["']""", text, flags=re.IGNORECASE)
        if not match:
            return ""
        return NoticiasModule._normalize_cover_url(match.group(1) or "", base_url=base_url)

    @staticmethod
    def _normalize_cover_url(candidate: Any, base_url: str = "") -> str:
        text = str(candidate or "").strip()
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        if text.lower().startswith(("http://", "https://")):
            return text
        if base_url:
            try:
                joined = urljoin(base_url, text)
                if str(joined).lower().startswith(("http://", "https://")):
                    return str(joined)
            except Exception:
                return ""
        return ""

    @staticmethod
    def _looks_like_image_url(url: str) -> bool:
        value = str(url or "").strip().lower()
        if not value:
            return False
        if re.search(r"\.(jpg|jpeg|png|webp|gif|bmp|svg)(\?|$)", value):
            return True
        return any(marker in value for marker in ("image", "thumbnail", "thumb", "cover", "media"))

    @staticmethod
    def _html_to_plain(value: str) -> str:
        raw = str(value or "")
        if not raw:
            return ""
        without_tags = re.sub(r"<[^>]+>", " ", raw)
        normalized = html.unescape(without_tags)
        return re.sub(r"\s+", " ", normalized).strip()
