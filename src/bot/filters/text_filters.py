"""Фильтры для текстовых сообщений"""

import re
from typing import Union, List
from aiogram.filters import BaseFilter
from aiogram.types import Message

class TextFilter(BaseFilter):
    """Фильтр для проверки текста сообщения"""
    
    def __init__(self, text: Union[str, List[str]], case_sensitive: bool = False):
        self.texts = [text] if isinstance(text, str) else text
        self.case_sensitive = case_sensitive
    
    async def __call__(self, message: Message) -> bool:
        """Проверка текста сообщения"""
        if not message.text:
            return False
        
        text = message.text if self.case_sensitive else message.text.lower()
        check_texts = self.texts if self.case_sensitive else [t.lower() for t in self.texts]
        
        return text in check_texts

class CommandFilter(BaseFilter):
    """Фильтр для проверки команд"""
    
    def __init__(self, commands: Union[str, List[str]]):
        self.commands = [commands] if isinstance(commands, str) else commands
    
    async def __call__(self, message: Message) -> bool:
        """Проверка команды"""
        if not message.text or not message.text.startswith('/'):
            return False
        
        command = message.text.split()[0][1:]  # Убираем '/' и берем первое слово
        return command in self.commands