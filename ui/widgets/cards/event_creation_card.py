# ui/widgets/cards/event_creation_card.py
"""
Card para criação de novos eventos na agenda
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QTextEdit,
                             QDateTimeEdit, QCheckBox, QGroupBox, QSpinBox,
                             QScrollArea, QFrame, QGridLayout, QTimeEdit,
                             QButtonGroup, QRadioButton, QStackedWidget, QListWidget)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QIcon, QColor
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import uuid
from.base_card import PhilosophyCard

class EventCreationCard(PhilosophyCard):
    """Card para criação manual de eventos na agenda"""
    
    # Sinais
    event_created = pyqtSignal(dict)  # Emite os dados do evento criado
    event_scheduled = pyqtSignal(str)  # Emite ID do evento agendado
    cancel_requested = pyqtSignal()    # Quando o usuário cancela
    
    # Constantes
    EVENT_TYPES = [
        ("casual", "🎯 Casual", "Evento geral"),
        ("leitura", "📚 Leitura", "Sessão de leitura"),
        ("producao", "✍️ Produção", "Escrita ou produção acadêmica"),
        ("revisao", "🔄 Revisão", "Revisão de conteúdo"),
        ("aula", "🎓 Aula", "Aula ou palestra"),
        ("orientacao", "👥 Orientação", "Orientação ou reunião"),
        ("grupo_estudo", "👨‍👩‍👧‍👦 Grupo", "Grupo de estudo"),
        ("refeicao", "🍽️ Refeição", "Refeição"),
        ("sono", "😴 Sono", "Descanso"),
        ("lazer", "🎮 Lazer", "Tempo livre"),
        ("transcricao", "📝 Transcrição", "Processamento de material"),
        ("checkin", "✅ Check-in", "Check-in diário")
    ]
    
    PRIORITIES = [
        ("low", "🔵 Baixa", "Prioridade baixa"),
        ("medium", "🟡 Média", "Prioridade padrão"),
        ("high", "🟠 Alta", "Prioridade alta"),
        ("fixed", "🔴 Fixa", "Evento fixo"),
        ("blocking", "⛔ Bloqueio", "Evento intransponível")
    ]
    
    RECURRENCE_TYPES = [
        ("none", "❌ Nenhuma", "Evento único"),
        ("daily", "📅 Diário", "Repete todos os dias"),
        ("weekly", "📆 Semanal", "Repete semanalmente"),
        ("weekdays", "🏢 Dias úteis", "Segunda a sexta"),
        ("custom", "⚙️ Personalizado", "Dias específicos")
    ]
    
    # Mapeamento de dias da semana
    WEEKDAYS = [
        ("mon", "Segunda", "Dia útil"),
        ("tue", "Terça", "Dia útil"),
        ("wed", "Quarta", "Dia útil"),
        ("thu", "Quinta", "Dia útil"),
        ("fri", "Sexta", "Dia útil"),
        ("sat", "Sábado", "Fim de semana"),
        ("sun", "Domingo", "Fim de semana")
    ]
    
    def __init__(self, agenda_controller=None, reading_manager=None, parent=None):
        super().__init__(parent)
        self.agenda_controller = agenda_controller
        self.reading_manager = reading_manager
        self.current_book_id = None
        
        # Estado interno
        self._setup_ui()
        self._setup_connections()
        self._load_defaults()
        
    def _setup_ui(self):
        """Configura a interface do card"""
        self.set_title("Novo Evento")
        
        # Container principal com scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        self.main_layout = QVBoxLayout(content_widget)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Formulário
        self._create_basic_info_section()
        self._create_datetime_section()
        self._create_recurrence_section()
        self._create_advanced_section()
        
        # Área de livros (mostrada apenas para eventos de leitura)
        self.book_selection_widget = self._create_book_selection_section()
        self.main_layout.addWidget(self.book_selection_widget)
        self.book_selection_widget.hide()
        
        # Botões de ação
        self._create_action_buttons()
        
        scroll_area.setWidget(content_widget)
        
        # Limpar layout atual e adicionar scroll area
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.content_layout.addWidget(scroll_area)
        
        # Rodapé
        self._setup_footer()
        
    def _create_basic_info_section(self):
        """Cria seção de informações básicas"""
        basic_group = QGroupBox("Informações Básicas")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(8)
        
        # Título
        basic_layout.addWidget(QLabel("Título:"), 0, 0)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Ex: Leitura da Metafísica")
        basic_layout.addWidget(self.title_input, 0, 1, 1, 3)
        
        # Descrição
        basic_layout.addWidget(QLabel("Descrição:"), 1, 0)
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setPlaceholderText("Detalhes do evento...")
        basic_layout.addWidget(self.desc_input, 1, 1, 1, 3)
        
        # Tipo de evento
        basic_layout.addWidget(QLabel("Tipo:"), 2, 0)
        self.type_combo = QComboBox()
        for value, text, tooltip in self.EVENT_TYPES:
            self.type_combo.addItem(text, value)
            idx = self.type_combo.count() - 1
            self.type_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
        basic_layout.addWidget(self.type_combo, 2, 1)
        
        # Prioridade
        basic_layout.addWidget(QLabel("Prioridade:"), 2, 2)
        self.priority_combo = QComboBox()
        for value, text, tooltip in self.PRIORITIES:
            self.priority_combo.addItem(text, value)
            idx = self.priority_combo.count() - 1
            self.priority_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
        basic_layout.addWidget(self.priority_combo, 2, 3)
        
        # Disciplina
        basic_layout.addWidget(QLabel("Disciplina:"), 3, 0)
        self.discipline_input = QLineEdit()
        self.discipline_input.setPlaceholderText("Ex: Filosofia, Ética...")
        basic_layout.addWidget(self.discipline_input, 3, 1, 1, 3)
        
        basic_group.setLayout(basic_layout)
        self.main_layout.addWidget(basic_group)
        
    def _create_datetime_section(self):
        """Cria seção de data e hora"""
        datetime_group = QGroupBox("Data e Horário")
        datetime_layout = QGridLayout()
        datetime_layout.setSpacing(8)
        
        # Data de início
        datetime_layout.addWidget(QLabel("Data Início:"), 0, 0)
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDateTime(QDateTime.currentDateTime())
        datetime_layout.addWidget(self.start_date_input, 0, 1)
        
        # Hora de início
        datetime_layout.addWidget(QLabel("Hora Início:"), 0, 2)
        self.start_time_input = QTimeEdit()
        self.start_time_input.setDisplayFormat("HH:mm")
        self.start_time_input.setTime(self.start_date_input.time())
        datetime_layout.addWidget(self.start_time_input, 0, 3)
        
        # Data de fim
        datetime_layout.addWidget(QLabel("Data Fim:"), 1, 0)
        self.end_date_input = QDateTimeEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        datetime_layout.addWidget(self.end_date_input, 1, 1)
        
        # Hora de fim
        datetime_layout.addWidget(QLabel("Hora Fim:"), 1, 2)
        self.end_time_input = QTimeEdit()
        self.end_time_input.setDisplayFormat("HH:mm")
        self.end_time_input.setTime(self.end_date_input.time().addSecs(3600))
        datetime_layout.addWidget(self.end_time_input, 1, 3)
        
        # Duração calculada
        datetime_layout.addWidget(QLabel("Duração:"), 2, 0)
        self.duration_label = QLabel("1 hora")
        datetime_layout.addWidget(self.duration_label, 2, 1)
        
        # Checkbox de dia inteiro
        self.all_day_check = QCheckBox("Dia inteiro")
        datetime_layout.addWidget(self.all_day_check, 2, 2, 1, 2)
        
        datetime_group.setLayout(datetime_layout)
        self.main_layout.addWidget(datetime_group)
        
    def _create_recurrence_section(self):
        """Cria seção de recorrência"""
        recurrence_group = QGroupBox("Recorrência")
        recurrence_layout = QVBoxLayout()
        
        # Tipo de recorrência
        self.recurrence_stack = QStackedWidget()
        
        # Nenhuma recorrência
        self.none_widget = QWidget()
        self.recurrence_stack.addWidget(self.none_widget)
        
        # Diário
        self.daily_widget = QWidget()
        daily_layout = QHBoxLayout()
        daily_layout.addWidget(QLabel("Repetir a cada"))
        self.daily_interval = QSpinBox()
        self.daily_interval.setMinimum(1)
        self.daily_interval.setMaximum(30)
        self.daily_interval.setValue(1)
        daily_layout.addWidget(self.daily_interval)
        daily_layout.addWidget(QLabel("dia(s)"))
        daily_layout.addStretch()
        self.daily_widget.setLayout(daily_layout)
        self.recurrence_stack.addWidget(self.daily_widget)
        
        # Semanal
        self.weekly_widget = QWidget()
        weekly_layout = QVBoxLayout()
        
        # Dias da semana
        days_group = QGroupBox("Dias da Semana")
        days_layout = QHBoxLayout()
        self.day_buttons = {}
        self.day_button_group = QButtonGroup()
        self.day_button_group.setExclusive(False)
        
        for value, text, tooltip in self.WEEKDAYS:
            btn = QCheckBox(text[:3])
            btn.setToolTip(tooltip)
            btn.setProperty("day_value", value)
            self.day_buttons[value] = btn
            self.day_button_group.addButton(btn)
            days_layout.addWidget(btn)
        
        days_group.setLayout(days_layout)
        weekly_layout.addWidget(days_group)
        
        # Intervalo semanal
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Repetir a cada"))
        self.weekly_interval = QSpinBox()
        self.weekly_interval.setMinimum(1)
        self.weekly_interval.setMaximum(52)
        self.weekly_interval.setValue(1)
        interval_layout.addWidget(self.weekly_interval)
        interval_layout.addWidget(QLabel("semana(s)"))
        interval_layout.addStretch()
        weekly_layout.addLayout(interval_layout)
        
        self.weekly_widget.setLayout(weekly_layout)
        self.recurrence_stack.addWidget(self.weekly_widget)
        
        # Dias úteis
        self.weekdays_widget = QWidget()
        weekdays_layout = QHBoxLayout()
        weekdays_layout.addWidget(QLabel("Repetir de segunda a sexta"))
        weekdays_layout.addStretch()
        self.weekdays_widget.setLayout(weekdays_layout)
        self.recurrence_stack.addWidget(self.weekdays_widget)
        
        # Personalizado
        self.custom_widget = QWidget()
        custom_layout = QVBoxLayout()
        custom_layout.addWidget(QLabel("Configuração personalizada (em desenvolvimento)"))
        self.custom_widget.setLayout(custom_layout)
        self.recurrence_stack.addWidget(self.custom_widget)
        
        # Combo para selecionar tipo
        recurrence_selector_layout = QHBoxLayout()
        recurrence_selector_layout.addWidget(QLabel("Tipo:"))
        self.recurrence_combo = QComboBox()
        for value, text, tooltip in self.RECURRENCE_TYPES:
            self.recurrence_combo.addItem(text, value)
            idx = self.recurrence_combo.count() - 1
            self.recurrence_combo.setItemData(idx, tooltip, Qt.ItemDataRole.ToolTipRole)
        recurrence_selector_layout.addWidget(self.recurrence_combo)
        recurrence_selector_layout.addStretch()
        
        recurrence_layout.addLayout(recurrence_selector_layout)
        recurrence_layout.addWidget(self.recurrence_stack)
        
        recurrence_group.setLayout(recurrence_layout)
        self.main_layout.addWidget(recurrence_group)
        
    def _create_advanced_section(self):
        """Cria seção de configurações avançadas"""
        advanced_group = QGroupBox("Configurações Avançadas")
        advanced_layout = QGridLayout()
        advanced_layout.setSpacing(8)
        
        # Dificuldade
        advanced_layout.addWidget(QLabel("Dificuldade:"), 0, 0)
        self.difficulty_slider = QSpinBox()
        self.difficulty_slider.setMinimum(1)
        self.difficulty_slider.setMaximum(5)
        self.difficulty_slider.setValue(3)
        advanced_layout.addWidget(self.difficulty_slider, 0, 1)
        
        # Flexibilidade
        self.flexible_check = QCheckBox("Evento flexível")
        self.flexible_check.setChecked(True)
        self.flexible_check.setToolTip("Pode ser movido/redimensionado")
        advanced_layout.addWidget(self.flexible_check, 0, 2)
        
        # Bloqueante
        self.blocking_check = QCheckBox("Evento bloqueante")
        self.blocking_check.setToolTip("Não pode ter outros eventos sobrepostos")
        advanced_layout.addWidget(self.blocking_check, 0, 3)
        
        # Tags
        advanced_layout.addWidget(QLabel("Tags:"), 1, 0)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("filosofia,metafisica,etica (separadas por vírgula)")
        advanced_layout.addWidget(self.tags_input, 1, 1, 1, 3)
        
        # Notas de progresso
        advanced_layout.addWidget(QLabel("Notas iniciais:"), 2, 0)
        self.progress_notes = QTextEdit()
        self.progress_notes.setMaximumHeight(60)
        self.progress_notes.setPlaceholderText("Observações iniciais...")
        advanced_layout.addWidget(self.progress_notes, 2, 1, 1, 3)
        
        advanced_group.setLayout(advanced_layout)
        self.main_layout.addWidget(advanced_group)
        
    def _create_book_selection_section(self):
        """Cria seção de seleção de livros (para eventos de leitura)"""
        book_widget = QGroupBox("Seleção de Livro")
        book_layout = QVBoxLayout()
        
        # Combo de livros disponíveis
        self.book_combo = QComboBox()
        self.book_combo.addItem("📚 Selecione um livro...", None)
        self._load_available_books()
        book_layout.addWidget(self.book_combo)
        
        # Informações do livro selecionado
        self.book_info_label = QLabel("")
        self.book_info_label.setWordWrap(True)
        book_layout.addWidget(self.book_info_label)
        
        # Botão para adicionar novo livro
        self.new_book_btn = QPushButton("➕ Adicionar Novo Livro")
        self.new_book_btn.setStyleSheet("""
            QPushButton {
                padding: 5px;
                background-color: #4A90E2;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3A7BC8;
            }
        """)
        book_layout.addWidget(self.new_book_btn)
        
        book_widget.setLayout(book_layout)
        return book_widget
        
    def _create_action_buttons(self):
        """Cria botões de ação"""
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Botão Cancelar
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #64748B;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        buttons_layout.addWidget(self.cancel_btn)
        
        # Botão Salvar
        self.save_btn = QPushButton("Salvar Evento")
        self.save_btn.setMinimumWidth(120)
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #10B981;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0EA271;
            }
        """)
        buttons_layout.addWidget(self.save_btn)
        
        self.main_layout.addLayout(buttons_layout)
        
    def _setup_footer(self):
        """Configura o rodapé do card"""
        # Limpar rodapé existente
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Status
        self.status_label = QLabel("Pronto para criar evento")
        self.status_label.setObjectName("footer_status")
        self.footer_layout.addWidget(self.status_label)
        
    def _setup_connections(self):
        """Configura conexões de sinais"""
        # Conecta botões
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        # Conecta mudanças de tipo de evento
        self.type_combo.currentIndexChanged.connect(self._on_event_type_changed)
        
        # Conecta mudanças de recorrência
        self.recurrence_combo.currentIndexChanged.connect(
            lambda idx: self.recurrence_stack.setCurrentIndex(idx)
        )
        
        # Conecta mudanças de datas/tempos
        self.start_date_input.dateTimeChanged.connect(self._update_duration)
        self.start_time_input.timeChanged.connect(self._update_duration)
        self.end_date_input.dateTimeChanged.connect(self._update_duration)
        self.end_time_input.timeChanged.connect(self._update_duration)
        self.all_day_check.toggled.connect(self._on_all_day_toggled)
        
        # Conecta seleção de livro
        if hasattr(self, 'book_combo'):
            self.book_combo.currentIndexChanged.connect(self._on_book_selected)
            self.new_book_btn.clicked.connect(self._on_new_book_clicked)
        
    def _load_defaults(self):
        """Carrega valores padrão"""
        # Define horários padrão (próxima hora redonda)
        now = QDateTime.currentDateTime()
        current_minute = now.time().minute()
        if current_minute < 30:
            start_time = now.addSecs((30 - current_minute) * 60)
        else:
            start_time = now.addSecs((60 - current_minute) * 60)
        
        end_time = start_time.addSecs(3600)  # 1 hora depois
        
        self.start_date_input.setDateTime(start_time)
        self.end_date_input.setDateTime(end_time)
        
        # Configura recorrência padrão
        self.recurrence_stack.setCurrentIndex(0)
        
        # Atualiza duração
        self._update_duration()
        
    def _load_available_books(self):
        """Carrega livros disponíveis do ReadingManager"""
        if not self.reading_manager:
            return
            
        try:
            books = self.reading_manager.list_books()
            self.book_combo.clear()
            self.book_combo.addItem("📚 Selecione um livro...", None)
            
            for book in books:
                title = book.get('title', 'Desconhecido')
                author = book.get('author', 'Autor desconhecido')
                progress = book.get('current_page', 0)
                total = book.get('total_pages', 0)
                
                display_text = f"{title} - {author} ({progress}/{total})"
                self.book_combo.addItem(display_text, book.get('id'))
                
        except Exception as e:
            print(f"Erro ao carregar livros: {e}")
            
    def _on_event_type_changed(self, index):
        """Lida com mudança no tipo de evento"""
        event_type = self.type_combo.currentData()
        
        # Mostra/oculta seção de livros para eventos de leitura
        if event_type == "leitura":
            self.book_selection_widget.show()
            self._load_available_books()
        else:
            self.book_selection_widget.hide()
            
    def _on_book_selected(self, index):
        """Lida com seleção de livro"""
        if index == 0:  # Item "Selecione um livro..."
            self.current_book_id = None
            self.book_info_label.setText("")
            return
            
        book_id = self.book_combo.currentData()
        self.current_book_id = book_id
        
        # Busca informações detalhadas do livro
        if self.reading_manager:
            try:
                progress = self.reading_manager.get_reading_progress(book_id)
                if progress:
                    title = progress.get('title', 'Desconhecido')
                    pages = progress.get('progress', '0/0')
                    percentage = progress.get('percentage', 0)
                    
                    info_text = f"<b>{title}</b><br>Progresso: {pages} ({percentage:.1f}%)"
                    self.book_info_label.setText(info_text)
                    
                    # Preenche título automaticamente se estiver vazio
                    if not self.title_input.text().strip():
                        self.title_input.setText(f"Leitura: {title}")
            except:
                pass
                
    def _on_new_book_clicked(self):
        """Abre diálogo para adicionar novo livro"""
        # Emite sinal para abrir diálogo de adição de livro
        # (Isso seria tratado pelo controller principal)
        self.book_selection_widget.hide()
        self.status_label.setText("Use o módulo de livros para adicionar novos livros")
        
    def _on_all_day_toggled(self, checked):
        """Lida com toggle de 'dia inteiro'"""
        if checked:
            # Configura para dia inteiro (00:00 - 23:59)
            start_date = self.start_date_input.date()
            self.start_time_input.setTime(QTime(0, 0))
            self.end_date_input.setDate(start_date)
            self.end_time_input.setTime(QTime(23, 59))
            self._update_duration()
            
    def _update_duration(self):
        """Atualiza label de duração"""
        start_dt = self.start_date_input.dateTime()
        end_dt = self.end_date_input.dateTime()
        
        if start_dt >= end_dt:
            self.duration_label.setText("⚠️ Data inválida")
            self.duration_label.setStyleSheet("color: #EF4444;")
            return
            
        # Calcula duração
        seconds = start_dt.secsTo(end_dt)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours == 0:
            duration_text = f"{minutes} minuto{'s' if minutes != 1 else ''}"
        elif minutes == 0:
            duration_text = f"{hours} hora{'s' if hours != 1 else ''}"
        else:
            duration_text = f"{hours}h {minutes}min"
            
        self.duration_label.setText(duration_text)
        self.duration_label.setStyleSheet("")
        
    def _on_save_clicked(self):
        """Lida com clique no botão Salvar"""
        # Validação básica
        if not self._validate_form():
            return
            
        # Prepara dados do evento
        event_data = self._prepare_event_data()
        
        # Se for evento de leitura com livro selecionado
        if event_data['type'] == 'leitura' and self.current_book_id:
            event_data['book_id'] = self.current_book_id
            # Usa agenda controller para alocação automática se disponível
            if self.agenda_controller:
                self._schedule_reading_events(event_data)
                return
                
        # Para outros tipos de evento, cria diretamente
        self._create_single_event(event_data)
        
    def _on_cancel_clicked(self):
        """Lida com clique no botão Cancelar"""
        self.cancel_requested.emit()
        
    def _validate_form(self) -> bool:
        """Valida os dados do formulário"""
        errors = []
        
        # Título obrigatório
        if not self.title_input.text().strip():
            errors.append("Título é obrigatório")
            
        # Validação de datas
        start_dt = self.start_date_input.dateTime()
        end_dt = self.end_date_input.dateTime()
        
        if start_dt >= end_dt:
            errors.append("Data/hora de início deve ser anterior ao fim")
            
        # Validação para eventos de leitura
        if self.type_combo.currentData() == "leitura":
            if not self.current_book_id:
                errors.append("Selecione um livro para eventos de leitura")
                
        if errors:
            error_text = "• " + "\n• ".join(errors)
            self.status_label.setText(f"❌ Erros:\n{error_text}")
            self.status_label.setStyleSheet("color: #EF4444;")
            return False
            
        return True
        
    def _prepare_event_data(self) -> dict:
        """Prepara dados do evento para envio"""
        # Informações básicas
        event_data = {
            'id': str(uuid.uuid4()),
            'title': self.title_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'type': self.type_combo.currentData(),
            'priority': self.priority_combo.currentData(),
            'discipline': self.discipline_input.text().strip(),
            'difficulty': self.difficulty_slider.value(),
            'is_flexible': self.flexible_check.isChecked(),
            'is_blocking': self.blocking_check.isChecked(),
            'all_day': self.all_day_check.isChecked(),
            'auto_generated': False,
            'completed': False
        }
        
        # Data e hora
        start_dt = self.start_date_input.dateTime()
        end_dt = self.end_date_input.dateTime()
        
        event_data['start'] = start_dt.toString(Qt.DateFormat.ISODate)
        event_data['end'] = end_dt.toString(Qt.DateFormat.ISODate)
        
        # Recorrência
        recurrence_type = self.recurrence_combo.currentData()
        event_data['recurrence'] = self._prepare_recurrence_data(recurrence_type)
        
        # Tags
        tags_text = self.tags_input.text().strip()
        if tags_text:
            event_data['tags'] = [tag.strip() for tag in tags_text.split(',')]
            
        # Notas
        notes = self.progress_notes.toPlainText().strip()
        if notes:
            event_data['progress_notes'] = [notes]
            
        # Metadados adicionais
        event_data['metadata'] = {
            'created_by': 'manual',
            'created_at': datetime.now().isoformat(),
            'recurrence_type': recurrence_type
        }
        
        return event_data
        
    def _prepare_recurrence_data(self, recurrence_type: str) -> dict:
        """Prepara dados de recorrência"""
        if recurrence_type == 'none':
            return {'type': 'none'}
            
        elif recurrence_type == 'daily':
            return {
                'type': 'daily',
                'interval': self.daily_interval.value(),
                'end_date': None  # Sem data de término definida
            }
            
        elif recurrence_type == 'weekly':
            selected_days = []
            for day_value, btn in self.day_buttons.items():
                if btn.isChecked():
                    selected_days.append(day_value)
                    
            return {
                'type': 'weekly',
                'interval': self.weekly_interval.value(),
                'days': selected_days,
                'end_date': None
            }
            
        elif recurrence_type == 'weekdays':
            return {
                'type': 'weekdays',
                'interval': 1,
                'days': ['mon', 'tue', 'wed', 'thu', 'fri'],
                'end_date': None
            }
            
        else:  # custom
            return {'type': 'custom'}
            
    def _create_single_event(self, event_data: dict):
        """Cria um evento único"""
        if self.agenda_controller:
            # Usa controller para criar evento
            event_id = self.agenda_controller.add_event(event_data)
            if event_id:
                self.status_label.setText("✅ Evento criado com sucesso!")
                self.status_label.setStyleSheet("color: #10B981;")
                self.event_created.emit(event_data)
                self.event_scheduled.emit(event_id)
            else:
                self.status_label.setText("❌ Erro ao criar evento")
                self.status_label.setStyleSheet("color: #EF4444;")
        else:
            # Fallback: emite dados para processamento externo
            self.event_created.emit(event_data)
            self.status_label.setText("✅ Evento preparado para criação")
            self.status_label.setStyleSheet("color: #10B981;")
            
    def _schedule_reading_events(self, event_data: dict):
        """Agenda eventos de leitura automaticamente"""
        try:
            # Extrai informações para alocação
            book_id = event_data['book_id']
            start_date = self.start_date_input.date().toString("yyyy-MM-dd")
            
            # Calcula páginas por dia baseado na duração
            duration_hours = event_data.get('duration_hours', 1)
            reading_speed = 10  # páginas por hora (padrão)
            pages_per_day = int(duration_hours * reading_speed)
            
            # Chama o agenda controller para alocação automática
            if hasattr(self.agenda_controller, 'allocate_reading_time_async'):
                self.status_label.setText("📅 Agendando tempo de leitura...")
                
                self.agenda_controller.allocate_reading_time_async(
                    book_id=book_id,
                    pages_per_day=pages_per_day,
                    strategy="balanced"
                )
                
                # Conecta ao sinal de conclusão
                self.agenda_controller.reading_allocated.connect(
                    lambda result: self._on_reading_scheduled(result, event_data)
                )
            else:
                # Fallback: cria evento único
                self._create_single_event(event_data)
                
        except Exception as e:
            print(f"Erro ao agendar leitura: {e}")
            self._create_single_event(event_data)
            
    def _on_reading_scheduled(self, result: dict, original_data: dict):
        """Lida com conclusão do agendamento de leitura"""
        if result.get('error'):
            self.status_label.setText(f"❌ {result['error']}")
            self.status_label.setStyleSheet("color: #EF4444;")
            return
            
        # Sucesso no agendamento
        sessions = result.get('total_sessions', 0)
        self.status_label.setText(f"✅ {sessions} sessões de leitura agendadas!")
        self.status_label.setStyleSheet("color: #10B981;")
        
        # Emite sinal com resultado
        self.event_scheduled.emit(f"reading_{result.get('book_id', 'unknown')}")
        
    def set_agenda_controller(self, controller):
        """Define o agenda controller"""
        self.agenda_controller = controller
        
    def set_reading_manager(self, manager):
        """Define o reading manager"""
        self.reading_manager = manager
        self._load_available_books()
        
    def clear_form(self):
        """Limpa o formulário"""
        self.title_input.clear()
        self.desc_input.clear()
        self.discipline_input.clear()
        self.tags_input.clear()
        self.progress_notes.clear()
        self.current_book_id = None
        self._load_defaults()
        self.status_label.setText("Pronto para criar evento")
        self.status_label.setStyleSheet("")
        
    def set_default_book(self, book_id: str):
        """Define um livro padrão para o formulário"""
        if self.reading_manager and book_id:
            # Encontra o índice do livro no combo
            for i in range(self.book_combo.count()):
                if self.book_combo.itemData(i) == book_id:
                    self.book_combo.setCurrentIndex(i)
                    break
                    
    def set_default_date(self, date_str: str):
        """Define uma data padrão"""
        try:
            date = QDate.fromString(date_str, "yyyy-MM-dd")
            if date.isValid():
                current_dt = self.start_date_input.dateTime()
                current_dt.setDate(date)
                self.start_date_input.setDateTime(current_dt)
                self.end_date_input.setDate(date)
        except:
            pass