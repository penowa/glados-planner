# src/core/integration/book_integration.py
"""
Sistema de integração completo para livros
"""
from pathlib import Path
from typing import Dict, Optional
import json
from datetime import datetime, timedelta

from ..modules.book_processor import BookProcessor, ProcessingQuality, ProcessingStatus
from ..modules.reading_manager import ReadingManager
from ..modules.agenda_manager import AgendaManager, EventPriority
from ..modules.obsidian.vault_manager import ObsidianVaultManager


class BookIntegrationSystem:
    """Sistema completo de integração de livros"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o sistema integrado
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        
        # Inicializa módulos
        self.vault_manager = ObsidianVaultManager()
        self.book_processor = BookProcessor(self.vault_manager)
        self.reading_manager = ReadingManager(str(self.vault_path))
        self.agenda_manager = AgendaManager(str(self.vault_path))
        
        # Configurações
        self.integration_config = {
            'auto_schedule': True,
            'default_reading_speed': 10.0,  # páginas/hora
            'default_quality': ProcessingQuality.STANDARD,
            'default_deadline_days': 30,
            'auto_generate_flashcards': True
        }
    
    def process_and_integrate_book(
        self,
        book_path: str,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Processa e integra um livro completo no sistema
        
        Args:
            book_path: Caminho para o arquivo do livro
            options: Opções de processamento
            
        Returns:
            Resultado da integração
        """
        if options is None:
            options = {}
        
        result = {
            'book_id': None,
            'processing_result': None,
            'reading_registered': False,
            'scheduled': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            # PASSO 1: Processar o livro
            print("📚 Analisando livro...")
            
            processing_result = self.book_processor.process_book(
                filepath=book_path,
                quality=options.get('quality', self.integration_config['default_quality']),
                schedule_night=options.get('schedule_night', False)
            )
            
            result['processing_result'] = processing_result
            
            if processing_result.status == ProcessingStatus.FAILED:
                result['errors'].append(f"Falha no processamento: {processing_result.error}")
                return result
            
            if processing_result.status == ProcessingStatus.SCHEDULED:
                result['warnings'].append("Livro agendado para processamento noturno")
                return result
            
            # PASSO 2: Registrar no sistema de leituras
            print("📖 Registrando livro no sistema de leituras...")
            
            metadata = processing_result.metadata
            book_id = self.reading_manager.add_book(
                title=metadata.title,
                author=metadata.author,
                total_pages=metadata.total_pages
            )
            
            result['book_id'] = book_id
            result['reading_registered'] = True
            
            # Atualizar progresso inicial (página 0)
            self.reading_manager.update_progress(
                book_id=book_id,
                current_page=0,
                notes=f"Livro adicionado em {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            # PASSO 3: Agendar na agenda (se configurado)
            if self.integration_config['auto_schedule']:
                print("🗓️  Agendando tempo de leitura...")
                
                # Calcula prazo padrão (30 dias a partir de hoje)
                deadline_date = datetime.now() + timedelta(
                    days=options.get('deadline_days', self.integration_config['default_deadline_days'])
                )
                
                # Aloca tempo de leitura
                allocation_result = self.agenda_manager.allocate_reading_time(
                    book_id=book_id,
                    pages_per_day=metadata.total_pages / 
                        options.get('deadline_days', self.integration_config['default_deadline_days']),
                    reading_speed=self.integration_config['default_reading_speed'],
                    strategy=options.get('strategy', 'balanced')
                )
                
                if 'error' not in allocation_result:
                    result['scheduled'] = True
                    result['allocation'] = allocation_result
                else:
                    result['warnings'].append(f"Não foi possível agendar: {allocation_result.get('error')}")
            
            # PASSO 4: Criar revisão espaçada futura
            if self.integration_config['auto_generate_flashcards']:
                print("🧠 Configurando revisão espaçada...")
                
                # Agenda transição para revisão após conclusão
                review_date = datetime.now() + timedelta(
                    days=options.get('review_days', 7)
                )
                
                # TODO: Integrar com ReviewSystem quando disponível
                result['warnings'].append("Sistema de revisão será configurado após conclusão")
            
            print("✅ Livro integrado com sucesso!")
            
        except Exception as e:
            result['errors'].append(f"Erro na integração: {str(e)}")
        
        return result
    
    def get_book_status(self, book_id: str) -> Dict:
        """
        Obtém status completo de um livro
        
        Args:
            book_id: ID do livro
            
        Returns:
            Status completo
        """
        status = {
            'book_id': book_id,
            'reading_progress': None,
            'schedule': None,
            'agenda_events': [],
            'next_reading_session': None
        }
        
        try:
            # Progresso de leitura
            reading_progress = self.reading_manager.get_reading_progress(book_id)
            if reading_progress:
                status['reading_progress'] = reading_progress
                
                # Agenda do livro
                schedule = self.reading_manager.generate_schedule(book_id)
                status['schedule'] = schedule
            
            # Eventos na agenda
            all_events = self.agenda_manager.events.values()
            book_events = [
                event for event in all_events
                if hasattr(event, 'book_id') and event.book_id == book_id
            ]
            
            # Ordena eventos futuros
            future_events = [
                event for event in book_events
                if event.start > datetime.now() and not event.completed
            ]
            future_events.sort(key=lambda x: x.start)
            
            status['agenda_events'] = [
                {
                    'title': event.title,
                    'start': event.start.strftime('%Y-%m-%d %H:%M'),
                    'end': event.end.strftime('%Y-%m-%d %H:%M'),
                    'type': event.type.value
                }
                for event in future_events[:5]  # Próximos 5 eventos
            ]
            
            if future_events:
                status['next_reading_session'] = {
                    'time': future_events[0].start.strftime('%Y-%m-%d %H:%M'),
                    'duration': future_events[0].duration_minutes()
                }
        
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def update_reading_progress(self, book_id: str, current_page: int, notes: str = "") -> Dict:
        """
        Atualiza progresso de leitura e ajusta agenda
        
        Args:
            book_id: ID do livro
            current_page: Página atual
            notes: Notas sobre a leitura
            
        Returns:
            Resultado da atualização
        """
        result = {
            'updated': False,
            'schedule_adjusted': False,
            'warnings': []
        }
        
        try:
            # Atualiza progresso
            updated = self.reading_manager.update_progress(book_id, current_page, notes)
            result['updated'] = updated
            
            if updated:
                # Obtém progresso atualizado
                progress = self.reading_manager.get_reading_progress(book_id)
                
                # Se atrasado (> 20% do planejado), ajusta agenda
                if 'percentage' in progress and progress['percentage'] < 80:
                    # Recalcula páginas por dia
                    remaining_pages = progress['total_pages'] - current_page
                    days_remaining = self._calculate_remaining_days(book_id)
                    
                    if days_remaining > 0:
                        new_pages_per_day = remaining_pages / days_remaining
                        
                        # Remove eventos futuros de leitura deste livro
                        self._reschedule_book(book_id, new_pages_per_day)
                        result['schedule_adjusted'] = True
                        result['warnings'].append(
                            f"Ajuste de agenda: {new_pages_per_day:.1f} páginas/dia"
                        )
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _calculate_remaining_days(self, book_id: str) -> int:
        """Calcula dias restantes para leitura"""
        progress = self.reading_manager.get_reading_progress(book_id)
        
        if not progress or 'estimated_completion' not in progress:
            return 30  # padrão
        
        try:
            completion_date = datetime.strptime(progress['estimated_completion'], '%Y-%m-%d')
            remaining = (completion_date - datetime.now()).days
            return max(1, remaining)  # mínimo 1 dia
        except:
            return 30
    
    def _reschedule_book(self, book_id: str, new_pages_per_day: float):
        """Reagenda eventos de leitura de um livro"""
        # Remove eventos futuros deste livro
        events_to_remove = []
        
        for event_id, event in self.agenda_manager.events.items():
            if (hasattr(event, 'book_id') and 
                event.book_id == book_id and 
                event.start > datetime.now() and
                not event.completed):
                events_to_remove.append(event_id)
        
        # Remove eventos
        for event_id in events_to_remove:
            del self.agenda_manager.events[event_id]
        
        # Cria nova alocação
        self.agenda_manager.allocate_reading_time(
            book_id=book_id,
            pages_per_day=new_pages_per_day,
            reading_speed=self.integration_config['default_reading_speed'],
            strategy='balanced'
        )
        
        # Salva agenda
        self.agenda_manager._save_events()
