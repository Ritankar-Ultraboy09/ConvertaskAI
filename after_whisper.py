import re
from num2words import num2words

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text
