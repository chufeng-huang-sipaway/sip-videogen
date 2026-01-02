"""Text utilities for packaging text handling."""
import json
def escape_text_for_prompt(text:str)->str:
 """JSON-encode text to preserve exact characters, then strip outer quotes.
 This preserves the literal text exactly (including quotes, newlines)
 while making it safe for prompt injection.
 """
 #json.dumps handles all escaping: " -> \", newline -> \\n, etc.
 encoded=json.dumps(text)
 #Strip the surrounding quotes that json.dumps adds
 return encoded[1:-1]
