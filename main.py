#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RCPSP - Планирование проектов с ограниченными ресурсами
Главный файл для запуска программы
"""

import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui import run_gui

if __name__ == "__main__":
    run_gui()