# ui/widgets/cards/vault_stats_card.py
"""
Card para exibir estatísticas do Obsidian Vault.
Integrado com VaultController para dados em tempo real.
"""

import json
from typing import Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QProgressBar, QToolTip)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QPoint
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QFont, 
                        QPen, QBrush, QFontMetrics, QIcon)

from .base_card import PhilosophyCard
from ui.controllers.vault_controller import VaultController


class VaultStatsCard(PhilosophyCard):
    """Card de estatísticas do Obsidian Vault com atualização em tempo real"""
    
    # Sinais
    sync_requested = pyqtSignal(str)  # 'from_obsidian', 'to_obsidian', 'all'
    refresh_requested = pyqtSignal()
    
    def __init__(self, vault_controller: VaultController, parent=None):
        super().__init__(parent)
        self.controller = vault_controller
        self.stats_data = {}
        self.connection_status = False
        self.last_sync_time = None
        
        # Timer para atualização periódica
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(30000)  # Atualizar a cada 30 segundos
        
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
        
        # Adicionar botões de ação ao cabeçalho
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.title_label)
        
        # Botões de ação
        self.setup_action_buttons()
        for btn in [self.sync_from_btn, self.sync_to_btn, self.refresh_btn]:
            header_layout.addWidget(btn)
        
        self.header_layout = header_layout
        
        # Área de conteúdo
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        
        # Status de conexão
        self.status_widget = self.create_status_widget()
        self.content_layout.addWidget(self.status_widget)
        
        # Estatísticas principais
        self.stats_grid = self.create_stats_grid()
        self.content_layout.addWidget(self.stats_grid)
        
        # Gráficos
        self.charts_container = QWidget()
        self.charts_layout = QHBoxLayout(self.charts_container)
        self.charts_layout.setSpacing(15)
        
        self.type_chart = TypeChartWidget()
        self.tag_chart = TagChartWidget()
        
        self.charts_layout.addWidget(self.type_chart)
        self.charts_layout.addWidget(self.tag_chart)
        
        self.content_layout.addWidget(self.charts_container)
        
        # Barra de progresso da sincronização
        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setVisible(False)
        self.sync_progress_bar.setTextVisible(True)
        self.sync_progress_bar.setFormat("Sincronizando... %p%")
        self.content_layout.addWidget(self.sync_progress_bar)
        
        self.content_area_layout.addWidget(self.content_widget)
        
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
        self.refresh_data()
        
    @pyqtSlot()
    def refresh_data(self):
        """Atualizar dados do vault"""
        self.controller.get_vault_stats()
        
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
        
        # Atualizar gráficos
        type_counts = stats.get('type_counts', {})
        tag_counts = stats.get('tag_counts', {})
        
        self.type_chart.update_data(type_counts)
        self.tag_chart.update_data(tag_counts)
        
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
        
    @pyqtSlot(str)
    def handle_sync_request(self, sync_type: str):
        """Processar requisição de sincronização"""
        if sync_type == 'from_obsidian':
            self.controller.sync_from_obsidian()
        elif sync_type == 'to_obsidian':
            # Para sincronização para o Obsidian, pedir confirmação
            # ou usar livro selecionado
            self.controller.sync_all_to_obsidian()
            
    def _auto_refresh(self):
        """Atualização automática periódica"""
        if self.connection_status:
            self.refresh_data()


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
        y = margin
        
        for i, (label, value) in enumerate(self.data.items()):
            # Barra
            bar_width = (value / max_value) * chart_width
            
            gradient = QLinearGradient(0, y, bar_width, y + bar_height)
            gradient.setColorAt(0, colors[i % len(colors)])
            gradient.setColorAt(1, colors[i % len(colors)].darker(120))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawRoundedRect(margin, y, bar_width, bar_height, 3, 3)
            
            # Rótulo e valor
            painter.setPen(QColor(200, 200, 200))
            
            # Label
            label_text = label if len(label) <= 12 else label[:10] + "..."
            painter.drawText(margin + bar_width + 10, y + bar_height / 2 + 4, label_text)
            
            # Valor
            value_text = str(value)
            value_width = painter.fontMetrics().horizontalAdvance(value_text)
            painter.drawText(margin + bar_width - value_width - 5, 
                           y + bar_height / 2 + 4, value_text)
            
            y += bar_height + 15
            
        # Título
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(margin, 15, "Tipos de Notas")
        
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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.data:
            self.draw_no_data_message(painter)
            return
            
        # Calcular tamanho máximo e mínimo
        max_value = max(self.data.values()) if self.data.values() else 1
        min_value = min(self.data.values()) if self.data.values() else 1
        
        # Cores para tags
        colors = [
            QColor(107, 142, 35),   # Verde oliva claro
            QColor(160, 82, 45),    # Sienna
            QColor(153, 50, 204),   # Roxo médio
            QColor(0, 139, 139),    # Ciano escuro
            QColor(139, 0, 139),    # Magenta escuro
        ]
        
        # Posicionar tags
        center_x = self.width() // 2
        center_y = self.height() // 2 - 10
        radius = min(center_x, center_y) - 20
        
        import math
        angle_step = 2 * math.pi / len(self.data)
        
        for i, (tag, value) in enumerate(self.data.items()):
            # Tamanho da fonte baseado na frequência
            font_size = 10 + int((value - min_value) / (max_value - min_value) * 8)
            font = QFont("Arial", font_size, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Cor baseada na posição
            color = colors[i % len(colors)]
            painter.setPen(QPen(color, 1))
            
            # Posição na nuvem (layout circular)
            angle = i * angle_step + (math.pi / 8)  # Offset para melhor distribuição
            x = center_x + radius * math.cos(angle) * 0.7
            y = center_y + radius * math.sin(angle) * 0.7
            
            # Ajustar posição para centralizar texto
            text_width = painter.fontMetrics().horizontalAdvance(tag)
            text_height = painter.fontMetrics().height()
            
            painter.drawText(int(x - text_width / 2), int(y + text_height / 3), tag)
            
        # Título
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(10, 15, "Tags Mais Usadas")
        
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