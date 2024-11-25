from flask import flash, redirect, request, url_for
from flask_login import current_user


class LoginRequiredMixin:
    def is_accessible(self) -> bool:
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        flash("Войдите для доступа к странице.")

        return redirect(url_for("core.index", next=request.endpoint))
