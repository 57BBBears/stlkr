from flask_wtf import FlaskForm
from flask_wtf.file import FileField, file_allowed, file_required, file_size
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import input_required


class CopyPasteImportForm(FlaskForm):
    urls = TextAreaField("Urls", validators=[input_required()])
    delimiter = StringField(
        "Разделитель", description="По умолчанию каждая ссылка с новой строки."
    )
    copy_paste = SubmitField("Import")


class CSVImportForm(FlaskForm):
    def __init__(self, max_file_size_kb: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file.validators.append(file_size(max_size=max_file_size_kb * 1024))
        self.file.description = f"Max {max_file_size_kb} Kb"

    file = FileField("Файл", validators=[file_required(), file_allowed(["csv"])])
    delimiter = StringField("Разделитель", default=",")
    csv = SubmitField("Import")
