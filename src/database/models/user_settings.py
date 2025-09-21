from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Decimal
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal as PyDecimal

from app.database.database import Base

class UserSettings(Base):
    """Настройки пользователя"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), unique=True, nullable=False, index=True)
    
    # Уведомления
    task_notifications = Column(Boolean, default=True, nullable=False)
    payment_notifications = Column(Boolean, default=True, nullable=False)
    referral_notifications = Column(Boolean, default=True, nullable=False)
    admin_notifications = Column(Boolean, default=True, nullable=False)
    
    # Приватность
    hide_profile = Column(Boolean, default=False, nullable=False)
    hide_stats = Column(Boolean, default=False, nullable=False)
    hide_from_leaderboard = Column(Boolean, default=False, nullable=False)
    allow_referral_mentions = Column(Boolean, default=True, nullable=False)
    
    # Язык и локализация
    language = Column(String(10), default="ru", nullable=False)  # ru, en
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Автовывод
    auto_withdraw_enabled = Column(Boolean, default=False, nullable=False)
    auto_withdraw_threshold = Column(Decimal(precision=15, scale=2), default=PyDecimal("0"))
    auto_withdraw_address = Column(Text, nullable=True)  # Адрес/реквизиты для вывода
    auto_withdraw_method = Column(String(50), nullable=True)  # card, crypto, etc
    
    # Безопасность
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    login_notifications = Column(Boolean, default=True, nullable=False)
    api_access_enabled = Column(Boolean, default=False, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связи
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, language={self.language})>"
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            'user_id': self.user_id,
            'notifications': {
                'tasks': self.task_notifications,
                'payments': self.payment_notifications,
                'referrals': self.referral_notifications,
                'admin': self.admin_notifications
            },
            'privacy': {
                'hide_profile': self.hide_profile,
                'hide_stats': self.hide_stats,
                'hide_from_leaderboard': self.hide_from_leaderboard,
                'allow_referral_mentions': self.allow_referral_mentions
            },
            'localization': {
                'language': self.language,
                'timezone': self.timezone
            },
            'auto_withdraw': {
                'enabled': self.auto_withdraw_enabled,
                'threshold': float(self.auto_withdraw_threshold),
                'address': self.auto_withdraw_address,
                'method': self.auto_withdraw_method
            },
            'security': {
                'two_factor_enabled': self.two_factor_enabled,
                'login_notifications': self.login_notifications,
                'api_access_enabled': self.api_access_enabled
            }
        }
