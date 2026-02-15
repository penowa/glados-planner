# ui/widgets/cards/vault_stats_card.py
"""
Card para exibir estatísticas do Obsidian Vault.
Integrado com VaultController para dados em tempo real.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QProgressBar, QToolTip,
                            QLineEdit, QTreeWidget, QTreeWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QPoint, QRectF
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QFont, 
                        QPen, QBrush, QFontMetrics, QIcon)

from .base_card import PhilosophyCard
from ui.controllers.vault_controller import VaultController


class VaultStatsCard(PhilosophyCard):
    """Card de estatísticas do Obsidian Vault com atualização em tempo real"""
    
    # Sinais
    sync_requested = pyqtSignal(str)  # 'from_obsidian', 'to_obsidian', 'all'
    refresh_requested = pyqtSignal()
    context_confirmed = pyqtSignal(dict)  # contexto de notas selecionadas
    
    def __init__(self, vault_controller: VaultController, parent=None):
        super().__init__(parent)
        self.controller = vault_controller
        self.stats_data = {}
        self.connection_status = False
        self.last_sync_time = None
        self.all_notes: List[Dict[str, Any]] = []
        self.selected_note_paths = set()
        
        self.setup_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def setup_ui(self):
        """Configurar interface do card de vault"""
        self.setMinimumSize(400, 300)
        
        # Título do card
        self.title_label.setText("📂 Obsidian Vault")
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #8B7355;
        """)
        
        # Botões de ação
        self.setup_action_buttons()
        self.footer_layout.addStretch()
        for btn in [self.sync_from_btn, self.sync_to_btn, self.refresh_btn, self.clear_cache_btn]:
            self.footer_layout.addWidget(btn)
        
        # Área de conteúdo principal do card
        self.vault_content_widget = QWidget()
        self.vault_content_layout = QVBoxLayout(self.vault_content_widget)
        self.vault_content_layout.setSpacing(10)
        
        # Status de conexão
        self.status_widget = self.create_status_widget()
        self.vault_content_layout.addWidget(self.status_widget)
        
        # Estatísticas principais
        self.stats_grid = self.create_stats_grid()
        self.vault_content_layout.addWidget(self.stats_grid)

        # Estrutura visual do vault + seleção de contexto
        self.notes_section = self.create_notes_context_section()
        self.vault_content_layout.addWidget(self.notes_section, 1)
        
        # Barra de progresso da sincronização
        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setVisible(False)
        self.sync_progress_bar.setTextVisible(True)
        self.sync_progress_bar.setFormat("Sincronizando... %p%")
        self.vault_content_layout.addWidget(self.sync_progress_bar)
        self.content_layout.addWidget(self.vault_content_widget)

    def create_notes_context_section(self) -> QWidget:
        """Cria seção de estrutura do vault e seleção de notas para contexto."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        section_title = QLabel("🗂️ Estrutura do Vault")
        section_title.setStyleSheet("color: #CCCCCC; font-weight: bold;")

        self.selected_count_label = QLabel("0 notas selecionadas")
        self.selected_count_label.setStyleSheet("color: #888888; font-size: 11px;")

        header.addWidget(section_title)
        header.addStretch()
        header.addWidget(self.selected_count_label)
        layout.addLayout(header)

        self.search_hint_label = QLabel(
            "Digite um termo e pressione Enter para buscar no vault. "
            "Nada é carregado até você pesquisar."
        )
        self.search_hint_label.setStyleSheet("color: #8EA6C6; font-size: 11px;")
        self.search_hint_label.setWordWrap(True)
        layout.addWidget(self.search_hint_label)

        self.notes_filter_input = QLineEdit()
        self.notes_filter_input.setPlaceholderText("Ex.: ética aristotélica, heidegger, #metafisica...")
        self.notes_filter_input.returnPressed.connect(self.search_notes_on_demand)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)
        search_row.addWidget(self.notes_filter_input, 1)

        self.search_btn = QPushButton("Buscar")
        self.search_btn.setToolTip("Buscar notas no vault")
        self.search_btn.clicked.connect(self.search_notes_on_demand)
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)

        self.notes_tree = QTreeWidget()
        self.notes_tree.setColumnCount(1)
        self.notes_tree.setHeaderLabels(["Item"])
        self.notes_tree.setRootIsDecorated(True)
        self.notes_tree.setAlternatingRowColors(False)
        self.notes_tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.notes_tree.itemChanged.connect(self._on_tree_item_changed)
        self.notes_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1A2E47;
                border: 1px solid #2E4D74;
                border-radius: 6px;
                color: #D6E6FF;
            }
            QTreeWidget::item {
                border: none;
                padding: 3px 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3E6AA1;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #223A5A;
                color: #DCEBFF;
                border: none;
                padding: 4px;
            }
        """)
        layout.addWidget(self.notes_tree, 1)

        actions_row = QHBoxLayout()

        self.clear_selection_btn = QPushButton("Limpar seleção")
        self.clear_selection_btn.clicked.connect(self.clear_selected_notes)

        self.confirm_context_btn = QPushButton("Enviar contexto para a GLaDOS")
        self.confirm_context_btn.clicked.connect(self.confirm_selected_context)

        actions_row.addWidget(self.clear_selection_btn)
        actions_row.addStretch()
        actions_row.addWidget(self.confirm_context_btn)
        layout.addLayout(actions_row)

        return widget
        
    def setup_action_buttons(self):
        """Configurar botões de ação"""
        # Botão sincronizar do Obsidian
        self.sync_from_btn = QPushButton("⬇️")
        self.sync_from_btn.setToolTip("Sincronizar do Obsidian")
        self.sync_from_btn.setFixedSize(30, 30)
        self.sync_from_btn.clicked.connect(
            lambda: self.sync_requested.emit('from_obsidian')
        )
        
        # Botão sincronizar para Obsidian
        self.sync_to_btn = QPushButton("⬆️")
        self.sync_to_btn.setToolTip("Sincronizar para Obsidian")
        self.sync_to_btn.setFixedSize(30, 30)
        self.sync_to_btn.clicked.connect(
            lambda: self.sync_requested.emit('to_obsidian')
        )
        
        # Botão atualizar
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Atualizar estatísticas")
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)

        self.clear_cache_btn = QPushButton("🧹")
        self.clear_cache_btn.setToolTip("Limpar cache de notas carregadas em memória")
        self.clear_cache_btn.setFixedSize(30, 30)
        self.clear_cache_btn.clicked.connect(self.clear_runtime_cache)
        
    def create_status_widget(self) -> QWidget:
        """Criar widget de status de conexão"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Ícone de status
        self.status_icon = QLabel("●")
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #888888;
        """)
        
        # Informações do vault
        self.vault_info = QLabel("Vault não conectado")
        self.vault_info.setStyleSheet("color: #888888;")
        
        # Última sincronização
        self.last_sync_label = QLabel("")
        self.last_sync_label.setStyleSheet("color: #666666; font-size: 11px;")
        
        layout.addWidget(self.status_icon)
        layout.addWidget(self.vault_info)
        layout.addStretch()
        layout.addWidget(self.last_sync_label)
        
        return widget
        
    def create_stats_grid(self) -> QWidget:
        """Criar grade de estatísticas principais"""
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setSpacing(15)
        grid.setContentsMargins(0, 0, 0, 0)
        
        # Labels de estatísticas
        self.total_notes_label = self.create_stat_label("📝 Total de Notas", "0")
        self.total_tags_label = self.create_stat_label("🏷️ Tags", "0")
        self.total_links_label = self.create_stat_label("🔗 Links", "0")
        self.vault_size_label = self.create_stat_label("💾 Tamanho", "0 MB")
        
        # Posicionar na grade
        grid.addWidget(self.total_notes_label[0], 0, 0)
        grid.addWidget(self.total_notes_label[1], 1, 0)
        
        grid.addWidget(self.total_tags_label[0], 0, 1)
        grid.addWidget(self.total_tags_label[1], 1, 1)
        
        grid.addWidget(self.total_links_label[0], 0, 2)
        grid.addWidget(self.total_links_label[1], 1, 2)
        
        grid.addWidget(self.vault_size_label[0], 0, 3)
        grid.addWidget(self.vault_size_label[1], 1, 3)
        
        return widget
        
    def create_stat_label(self, title: str, value: str):
        """Criar par de labels (título e valor)"""
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #AAAAAA;
            font-size: 12px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            color: #E6E6E6;
            font-size: 18px;
            font-weight: bold;
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        return title_label, value_label
        
    def setup_connections(self):
        """Conectar sinais da controladora"""
        # Status do vault
        self.controller.vault_status_changed.connect(self.on_vault_status_changed)
        self.controller.vault_stats_updated.connect(self.on_vault_stats_updated)
        
        # Sincronização
        self.controller.sync_started.connect(self.on_sync_started)
        self.controller.sync_progress.connect(self.on_sync_progress)
        self.controller.sync_completed.connect(self.on_sync_completed)
        self.controller.error_occurred.connect(self.on_error)
        
        # Sinais internos
        self.sync_requested.connect(self.handle_sync_request)
        self.refresh_requested.connect(self.refresh_data)
        
    def load_initial_data(self):
        """Carregar dados iniciais"""
        self.controller.check_vault_connection()
        self.notes_tree.clear()
        self._update_selected_count_label()
        self.search_hint_label.setText(
            "Conectado em modo leve. Nada será carregado até você pesquisar ou clicar em atualizar stats."
        )
        
    @pyqtSlot()
    def refresh_data(self):
        """Atualizar dados do vault"""
        self.search_hint_label.setText("Atualizando estatísticas do vault...")
        self.controller.get_vault_stats()

    @pyqtSlot()
    def search_notes_on_demand(self):
        """Carrega notas somente quando o usuário pesquisar."""
        query = self.notes_filter_input.text().strip()
        if not query:
            self.search_hint_label.setText("Informe um termo para buscar no vault.")
            return

        self.search_hint_label.setText(f"Buscando por: '{query}'...")
        try:
            self.all_notes = self.controller.search_notes(query, search_in_content=True)
            available_paths = {note.get("path") for note in self.all_notes if note.get("path")}
            self.selected_note_paths = {p for p in self.selected_note_paths if p in available_paths}
            self.refresh_notes_tree()

            if self.all_notes:
                self.search_hint_label.setText(
                    f"{len(self.all_notes)} resultado(s) para '{query}'. "
                    "Selecione as notas para enviar contexto."
                )
            else:
                self.search_hint_label.setText(f"Nenhum resultado para '{query}'.")
        except Exception as e:
            self.all_notes = []
            self.selected_note_paths.clear()
            self.refresh_notes_tree()
            self.search_hint_label.setText(f"Erro ao buscar: {e}")

    @pyqtSlot()
    def clear_runtime_cache(self):
        """Limpa caches locais e do manager para reduzir RAM."""
        try:
            self.controller.clear_cache(clear_manager_cache=True)
        except Exception:
            # Fallback silencioso para não quebrar UI.
            pass
        self.all_notes = []
        self.selected_note_paths.clear()
        self.notes_tree.clear()
        self.search_hint_label.setText(
            "Cache limpo. Faça uma nova busca para carregar notas novamente."
        )
        self._update_selected_count_label()

    def refresh_notes_tree(self):
        """Atualiza árvore de notas no formato autor -> obra -> nota."""
        if not hasattr(self, "notes_tree"):
            return

        selected_paths = set(self.selected_note_paths)
        tree_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

        for note in self.all_notes:
            author_name, work_name = self._extract_author_work(note)
            tree_data[author_name][work_name].append(note)

        self.notes_tree.blockSignals(True)
        self.notes_tree.clear()

        for author_name in sorted(tree_data.keys(), key=str.lower):
            works_map = tree_data[author_name]
            author_notes_count = sum(len(notes) for notes in works_map.values())
            author_item = QTreeWidgetItem([f"👤 {author_name} ({author_notes_count})"])
            author_item.setFlags(author_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            author_item.setBackground(0, QBrush(QColor("#1A304F")))
            author_item.setForeground(0, QBrush(QColor("#E4EEFF")))
            self.notes_tree.addTopLevelItem(author_item)

            for work_name in sorted(works_map.keys(), key=str.lower):
                notes = works_map[work_name]
                work_item = QTreeWidgetItem([f"📚 {work_name} ({len(notes)})"])
                work_item.setFlags(work_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                work_item.setBackground(0, QBrush(QColor("#203958")))
                work_item.setForeground(0, QBrush(QColor("#D7E8FF")))
                author_item.addChild(work_item)

                sorted_notes = sorted(notes, key=lambda n: n.get("title", "").lower())
                for idx, note in enumerate(sorted_notes):
                    path = note.get("path", "")
                    note_item = QTreeWidgetItem([
                        f"{note.get('icon', '📝')} {note.get('title', 'Sem título')}"
                    ])
                    note_item.setFlags(note_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    note_item.setData(0, Qt.ItemDataRole.UserRole, note)
                    row_color = QColor("#223A5A") if idx % 2 == 0 else QColor("#29466C")
                    text_color = QBrush(QColor("#D8E8FF"))
                    note_item.setBackground(0, QBrush(row_color))
                    note_item.setForeground(0, text_color)
                    note_item.setCheckState(
                        0,
                        Qt.CheckState.Checked if path in selected_paths else Qt.CheckState.Unchecked
                    )
                    work_item.addChild(note_item)

                work_item.setExpanded(True)
            author_item.setExpanded(True)

        self.notes_tree.blockSignals(False)
        self._update_selected_count_label()

    def _extract_author_work(self, note: Dict[str, Any]) -> tuple[str, str]:
        """Extrai autor e obra para organização em árvore."""
        note_path = str(note.get("path", "") or "")
        frontmatter = note.get("frontmatter") or {}

        fm_author = str(frontmatter.get("author", "")).strip()
        fm_work = str(
            frontmatter.get("book")
            or frontmatter.get("obra")
            or frontmatter.get("work")
            or ""
        ).strip()

        try:
            parts = list(Path(note_path).parts)
        except Exception:
            parts = []

        author_name = fm_author
        work_name = fm_work

        # Padrão esperado: 01-LEITURAS/Autor/Obra/Nota.md
        if len(parts) >= 4 and not author_name:
            author_name = parts[1]
        if len(parts) >= 4 and not work_name:
            work_name = parts[2]

        # Fallbacks para caminhos fora do padrão
        if not author_name:
            author_name = parts[-3] if len(parts) >= 3 else "Sem autor"
        if not work_name:
            if len(parts) >= 2:
                work_name = parts[-2]
            else:
                work_name = "Sem obra"

        return author_name, work_name

    def _on_tree_item_changed(self, item: QTreeWidgetItem, _column: int):
        """Atualiza contador quando checkboxes mudam."""
        if item.childCount() > 0:
            return
        note = item.data(0, Qt.ItemDataRole.UserRole) or {}
        note_path = note.get("path")
        if note_path:
            if item.checkState(0) == Qt.CheckState.Checked:
                self.selected_note_paths.add(note_path)
            else:
                self.selected_note_paths.discard(note_path)
        self._update_selected_count_label()

    def _iter_leaf_items(self):
        """Itera itens folha (notas) da árvore."""
        def walk(item: QTreeWidgetItem):
            if item.childCount() == 0:
                yield item
                return
            for idx in range(item.childCount()):
                yield from walk(item.child(idx))

        for i in range(self.notes_tree.topLevelItemCount()):
            yield from walk(self.notes_tree.topLevelItem(i))

    def get_selected_note_paths(self) -> List[str]:
        """Retorna caminhos das notas selecionadas."""
        return sorted(self.selected_note_paths)

    def get_selected_notes(self) -> List[Dict[str, Any]]:
        """Retorna metadados completos das notas selecionadas (sob demanda)."""
        selected = []
        for note_path in sorted(self.selected_note_paths):
            note = self.controller.get_note(note_path)
            if note:
                selected.append(note)
        return selected

    def clear_selected_notes(self):
        """Limpa seleção de notas."""
        self.selected_note_paths.clear()
        if not hasattr(self, "notes_tree"):
            return
        self.notes_tree.blockSignals(True)
        for item in self._iter_leaf_items():
            item.setCheckState(0, Qt.CheckState.Unchecked)
        self.notes_tree.blockSignals(False)
        self._update_selected_count_label()

    def _update_selected_count_label(self):
        """Atualiza label com quantidade de notas selecionadas."""
        selected_count = len(self.selected_note_paths)
        self.selected_count_label.setText(f"{selected_count} nota(s) selecionada(s)")

    def confirm_selected_context(self):
        """Confirma notas selecionadas e emite contexto para o card GLaDOS."""
        selected_notes = self.get_selected_notes()
        if not selected_notes:
            self.context_confirmed.emit({
                "notes": [],
                "summary": "Nenhuma nota selecionada",
            })
            return

        payload = {
            "notes": selected_notes,
            "summary": f"{len(selected_notes)} nota(s) selecionada(s) do vault",
            "stats": self.stats_data,
        }
        self.context_confirmed.emit(payload)
        
    @pyqtSlot(dict)
    def on_vault_status_changed(self, status: Dict[str, Any]):
        """Atualizar status de conexão"""
        self.connection_status = status.get('connected', False)
        
        if self.connection_status:
            self.status_icon.setText("●")
            self.status_icon.setStyleSheet("""
                font-size: 20px;
                font-weight: bold;
                color: #4CAF50;
            """)
            
            vault_path = status.get('path', 'Desconhecido')
            # Encurtar caminho se muito longo
            if len(vault_path) > 40:
                vault_path = "..." + vault_path[-37:]
                
            self.vault_info.setText(f"Conectado: {vault_path}")
            self.vault_info.setStyleSheet("color: #4CAF50;")
            
            # Atualizar estatísticas se disponíveis
            if 'stats' in status and status['stats']:
                self.update_stats_display(status['stats'])
        else:
            self.status_icon.setText("●")
            self.status_icon.setStyleSheet("""
                font-size: 20px;
                font-weight: bold;
                color: #F44336;
            """)
            self.vault_info.setText("Vault não conectado")
            self.vault_info.setStyleSheet("color: #F44336;")
            
    @pyqtSlot(dict)
    def on_vault_stats_updated(self, stats: Dict[str, Any]):
        """Atualizar estatísticas do vault"""
        self.stats_data = stats
        self.update_stats_display(stats)
        self.last_sync_time = "Agora"
        self.update_last_sync_label()
        
    def update_stats_display(self, stats: Dict[str, Any]):
        """Atualizar a exibição das estatísticas"""
        # Estatísticas principais
        self.total_notes_label[1].setText(str(stats.get('total_notes', 0)))
        self.total_tags_label[1].setText(str(len(stats.get('tag_counts', {}))))
        self.total_links_label[1].setText(str(stats.get('total_links', 0)))
        
        vault_size = stats.get('vault_size_mb', 0)
        self.vault_size_label[1].setText(f"{vault_size:.1f} MB")
        
    def update_last_sync_label(self):
        """Atualizar label da última sincronização"""
        if self.last_sync_time:
            self.last_sync_label.setText(f"Última atualização: {self.last_sync_time}")
            
    @pyqtSlot(str)
    def on_sync_started(self, sync_type: str):
        """Início da sincronização"""
        self.sync_progress_bar.setVisible(True)
        self.sync_progress_bar.setValue(0)
        
        # Desabilitar botões durante sincronização
        self.sync_from_btn.setEnabled(False)
        self.sync_to_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.clear_cache_btn.setEnabled(False)
        
    @pyqtSlot(int, str)
    def on_sync_progress(self, percent: int, message: str):
        """Progresso da sincronização"""
        self.sync_progress_bar.setValue(percent)
        self.sync_progress_bar.setFormat(f"{message}... %p%")
        
    @pyqtSlot(dict)
    def on_sync_completed(self, result: Dict[str, Any]):
        """Sincronização concluída"""
        self.sync_progress_bar.setVisible(False)
        
        # Reabilitar botões
        self.sync_from_btn.setEnabled(True)
        self.sync_to_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.clear_cache_btn.setEnabled(True)
        
        # Atualizar dados se sincronização bem sucedida
        if result.get('success', False):
            self.last_sync_time = "Agora"
            self.update_last_sync_label()
            self.refresh_data()
            
    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """Erro na operação"""
        self.vault_info.setText(f"Erro: {error_message[:30]}...")
        self.vault_info.setStyleSheet("color: #F44336;")
        
        # Garantir que botões estão habilitados
        self.sync_from_btn.setEnabled(True)
        self.sync_to_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.clear_cache_btn.setEnabled(True)
        
    @pyqtSlot(str)
    def handle_sync_request(self, sync_type: str):
        """Processar requisição de sincronização"""
        if sync_type == 'from_obsidian':
            self.controller.sync_from_obsidian()
        elif sync_type == 'to_obsidian':
            # Para sincronização para o Obsidian, pedir confirmação
            # ou usar livro selecionado
            self.controller.sync_all_to_obsidian()
            
class TypeChartWidget(QWidget):
    """Widget de gráfico para tipos de notas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.setMinimumSize(180, 120)
        
    def update_data(self, data: Dict[str, int]):
        """Atualizar dados do gráfico"""
        self.data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True)[:5])  # Top 5
        self.update()
        
    def paintEvent(self, event):
        """Desenhar gráfico de barras horizontais"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if not self.data:
                self.draw_no_data_message(painter)
                return
                
            # Configurar área
            margin = 10
            chart_height = self.height() - 40
            chart_width = self.width() - 120
            
            # Calcular máximo para escala
            max_value = max(self.data.values()) if self.data.values() else 1
            
            # Cores para as barras
            colors = [
                QColor(85, 107, 47),   # Verde oliva
                QColor(139, 115, 85),  # Sépia
                QColor(128, 0, 0),     # Vermelho escuro
                QColor(72, 61, 139),   # Azul escuro
                QColor(139, 69, 19),   # Marrom sela
            ]
            
            # Desenhar barras
            bar_height = (chart_height - (len(self.data) - 1) * 15) / len(self.data)
            y = float(margin)
            
            for i, (label, value) in enumerate(self.data.items()):
                bar_width = (value / max_value) * chart_width
                
                gradient = QLinearGradient(0.0, y, bar_width, y + bar_height)
                gradient.setColorAt(0, colors[i % len(colors)])
                gradient.setColorAt(1, colors[i % len(colors)].darker(120))
                
                painter.setBrush(QBrush(gradient))
                painter.setPen(QPen(QColor(60, 60, 60), 1))
                painter.drawRoundedRect(QRectF(float(margin), y, float(bar_width), float(bar_height)), 3.0, 3.0)
                
                painter.setPen(QColor(200, 200, 200))
                label_text = label if len(label) <= 12 else label[:10] + "..."
                painter.drawText(int(margin + bar_width + 10), int(y + bar_height / 2 + 4), label_text)
                
                value_text = str(value)
                value_width = painter.fontMetrics().horizontalAdvance(value_text)
                painter.drawText(int(margin + bar_width - value_width - 5), int(y + bar_height / 2 + 4), value_text)
                
                y += bar_height + 15
                
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(margin, 15, "Tipos de Notas")
        finally:
            painter.end()
        
    def draw_no_data_message(self, painter):
        """Desenhar mensagem quando não há dados"""
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Arial", 10))
        
        text = "Sem dados disponíveis"
        text_width = painter.fontMetrics().horizontalAdvance(text)
        text_height = painter.fontMetrics().height()
        
        x = (self.width() - text_width) // 2
        y = (self.height() - text_height) // 2
        
        painter.drawText(x, y, text)


class TagChartWidget(QWidget):
    """Widget de nuvem de tags"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.setMinimumSize(180, 120)
        
    def update_data(self, data: Dict[str, int]):
        """Atualizar dados das tags"""
        self.data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True)[:8])  # Top 8
        self.update()
        
    def paintEvent(self, event):
        """Desenhar nuvem de tags"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if not self.data:
                self.draw_no_data_message(painter)
                return
                
            max_value = max(self.data.values()) if self.data.values() else 1
            min_value = min(self.data.values()) if self.data.values() else 1
            span = max(1, max_value - min_value)
            
            colors = [
                QColor(107, 142, 35),   # Verde oliva claro
                QColor(160, 82, 45),    # Sienna
                QColor(153, 50, 204),   # Roxo médio
                QColor(0, 139, 139),    # Ciano escuro
                QColor(139, 0, 139),    # Magenta escuro
            ]
            
            center_x = self.width() // 2
            center_y = self.height() // 2 - 10
            radius = min(center_x, center_y) - 20
            
            import math
            angle_step = 2 * math.pi / len(self.data)
            
            for i, (tag, value) in enumerate(self.data.items()):
                font_size = 10 + int((value - min_value) / span * 8)
                font = QFont("Arial", font_size, QFont.Weight.Bold)
                painter.setFont(font)
                
                color = colors[i % len(colors)]
                painter.setPen(QPen(color, 1))
                
                angle = i * angle_step + (math.pi / 8)
                x = center_x + radius * math.cos(angle) * 0.7
                y = center_y + radius * math.sin(angle) * 0.7
                
                text_width = painter.fontMetrics().horizontalAdvance(tag)
                text_height = painter.fontMetrics().height()
                
                painter.drawText(int(x - text_width / 2), int(y + text_height / 3), tag)
                
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(10, 15, "Tags Mais Usadas")
        finally:
            painter.end()
        
    def draw_no_data_message(self, painter):
        """Desenhar mensagem quando não há dados"""
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Arial", 10))
        
        text = "Sem tags disponíveis"
        text_width = painter.fontMetrics().horizontalAdvance(text)
        text_height = painter.fontMetrics().height()
        
        x = (self.width() - text_width) // 2
        y = (self.height() - text_height) // 2
        
        painter.drawText(x, y, text)
