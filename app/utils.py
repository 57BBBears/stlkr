def clear_url(url: str) -> str:
    if url := str(url).strip().lower():
        url_start = url.find(' ') + 1
        if url_start:
            url = url[url_start:].strip()

    return url


def text_to_list(text: str, sep='\r\n') -> list:
    text_list = text.split(sep)

    return [x for x in map(clear_url, text_list) if x]

def populate_object(obj, form, exclude=[]):
    for field_name, field_value in form._fields.items():
        if field_name in exclude:
            continue

        if hasattr(obj, field_name):
            setattr(obj, field_name, field_value.data)