import json
import os
import re

# Настройки
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Директория скрипта
DICTIONARY_FILE = os.path.join(BASE_DIR, "..", "terms_map.json")
INPUT_FOLDER = os.path.join(BASE_DIR, "..", "raw_data")        # Папка с исходными файлами
OUTPUT_FOLDER = os.path.join(BASE_DIR, "..", "knowledge_base")      # Папка для обработанных файлов (None для замены на месте

def keys_to_lower(obj):
    # Создаем новый словарь с ключами в нижнем регистре
    new_dict = {}
    for key, value in obj.items():
        new_dict[key.lower()] = value
    return new_dict

# Загружаем словарь
with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
    replacements = json.load(f, object_hook=keys_to_lower)

# Создаем выходную папку
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Создаем паттерн для поиска слов
words = list(replacements.keys())
symbols_pattern = r'(\[(\d|\w)+\]|\\n|\\t|\\d)'
pattern = re.compile(r'(' + '|'.join(words) + r')', re.IGNORECASE)

# Функция замены
def replace_match(match):
    word = match.group(0).lower()
    return replacements.get(word, match.group(0))

# Обрабатываем все текстовые файлы
for filename in os.listdir(INPUT_FOLDER):
    if filename.endswith('.md'):
        with open(os.path.join(INPUT_FOLDER, filename), 'r', encoding='utf-8') as f:
            content = f.read()

        # Заменяем слова
        new_content = pattern.sub(replace_match, content)
        
        # Сохраняем результат
        with open(os.path.join(OUTPUT_FOLDER, filename), 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Обработан: {filename}")

print("Готово!")