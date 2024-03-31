from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from redis.exceptions import ConnectionError, ResponseError
from rq.exceptions import NoSuchJobError
from sqlalchemy import and_, bindparam, desc, func, insert

import src.models
from src import db
from src.core.forms import (
    ClusterAddForm,
    ClusterForm,
    DataFrameCheckForm,
    DataFrameForm,
    DataFrameSelectorsForm,
    EmptyForm,
    PropertiesForm,
)
from src.core.utils.query import get_checked_urls_stmt, get_dataframe_selectors
from src.core.utils.text import parse_data_by_xpath, populate_object, text_to_list
from src.models import (
    Check,
    Cluster,
    Dataframe,
    DataframeCluster,
    DataframeProperty,
    Property,
    Url,
    UrlCheck,
    UrlProperty,
)

bp = Blueprint("core", __name__, template_folder="templates", static_folder="static")


@bp.route("/")
def index():
    per_page = request.args.get(
        "per_page", current_app.config["ITEMS_PER_PAGE"], type=int
    )
    df = Dataframe.query.order_by(Dataframe.id).paginate(per_page=per_page)
    clusters = Cluster.query.order_by(Cluster.id)

    return render_template(
        "core/index.html", title="Админка", dataframes=df, clusters=clusters
    )


@bp.route("/settings/", methods=["GET", "POST"])
def settings():
    properties = Property.query.order_by("id").all()
    form = PropertiesForm()

    if request.method == "GET" and properties:
        for prop in properties:
            form.properties.append_entry(prop)

    for _ in range(len(properties) - len(form.properties.entries) + 5):
        # allways show additional 5 empty forms
        form.properties.append_entry()

    if form.validate_on_submit():
        del_props = []
        add_props = []
        update_props = []

        for i in range(len(form.properties)):
            # print(form.properties[i].delete.data)

            if form.properties[i].data["id"] and form.properties[i].data["delete"]:
                # delete property if checkbox is checked
                del_props.append(form.properties[i].data["id"])
            elif (
                not form.properties[i].data["id"]
                and form.properties[i].data["name"]
                and form.properties[i].data["code"]
            ):
                # add property if name and code are filled
                add_props.append(
                    {
                        "name": form.properties[i].data["name"],
                        "code": form.properties[i].data["code"],
                    }
                )
            elif form.properties[i].data["id"] and (
                form.properties[i].data["name"] != properties[i].name
                or form.properties[i].data["code"] != properties[i].code
            ):
                # update property if name or code has been changed
                update_props.append(
                    {
                        "pk": form.properties[i].data["id"],
                        "name": form.properties[i].data["name"],
                        "code": form.properties[i].data["code"],
                    }
                )

        if del_props:
            db.session.execute(
                Property.__table__.delete().where(Property.id.in_(del_props))
            )

        if update_props:
            stmt = (
                Property.__table__.update()
                .where(Property.__table__.c.id == bindparam("pk"))
                .values(name=bindparam("name"), code=bindparam("code"))
            )
            db.session.execute(stmt, update_props)

        if add_props:
            db.session.execute(Property.__table__.insert().values(add_props))

        db.session.commit()

        flash("Настройки обновлены.")

        return redirect(url_for("core.settings"))

    return render_template("core/settings.html", title="Настройки", form=form)


@bp.route("/dataframe/<pk>/selectors/", methods=["GET", "POST"])
def dataframe_selectors(pk):
    df = Dataframe.query.get_or_404(pk)
    all_properties = Property.query.order_by("id").all()
    # select properties of current dataframe
    df_properties = (
        DataframeProperty.query.filter_by(dataframe_id=df.id)
        .order_by(DataframeProperty.id)
        .all()
    )
    df_selectors = {}
    for prop in df_properties:
        df_selectors[prop.property_id] = prop.selector

    # df_props = db.session.query(Property, DataFrameProperty
    # ).filter(DataFrameProperty.property_id==Property.id,
    # DataFrameProperty.dataframe_id==df.id)

    form = DataFrameSelectorsForm()
    if request.method == "GET":
        for prop in all_properties:
            # if dataframe has a selector for the property show it
            cur_selector = df_selectors[prop.id] if prop.id in df_selectors else ""
            form.selectors.append_entry(
                {"id": prop.id, "property": prop, "selector": cur_selector}
            )

    if form.validate_on_submit():
        update_props = []
        add_props = []
        del_props = []
        for form_data in form.selectors.data:
            if (
                form_data["selector"]
                and int(form_data["id"]) in df_selectors
                and form_data["selector"] != df_selectors[int(form_data["id"])]
            ):
                # update selector
                update_props.append(
                    {
                        "prop_id": form_data["id"],
                        "selector": form_data["selector"].strip(),
                    }
                )
            elif form_data["selector"] and int(form_data["id"]) not in df_selectors:
                # add new selector
                add_props.append(
                    {
                        "dataframe_id": df.id,
                        "property_id": form_data["id"],
                        "selector": form_data["selector"].strip(),
                    }
                )
            elif int(form_data["id"]) in df_selectors and not form_data["selector"]:
                # delete selectors from the dataframe
                del_props.append(form_data["id"])

        if update_props:
            stmt = (
                DataframeProperty.__table__.update()
                .where(
                    DataframeProperty.dataframe_id == df.id,
                    DataframeProperty.property_id == bindparam("prop_id"),
                )
                .values(selector=bindparam("selector"))
            )

            db.session.execute(stmt, update_props)

        if add_props:
            db.session.execute(DataframeProperty.__table__.insert().values(add_props))

        if del_props:
            db.session.execute(
                DataframeProperty.__table__.delete().where(
                    DataframeProperty.dataframe_id == df.id,
                    DataframeProperty.property_id.in_(del_props),
                )
            )

        if any([update_props, add_props, del_props]):
            db.session.commit()
            flash("Селекторы изменены.")

        return redirect(url_for("core.dataframe", pk=df.id))

    return render_template(
        "core/dataframe_selectors.html",
        title=f'Селекторы датафрейма "{df.name}"',
        form=form,
    )


@bp.route("/url/<pk>/")
def url(pk):
    urls_stmt = (
        db.session.query(
            Url.url,
            Check.name.label("check_name"),
            Property.name.label("property_name"),
            UrlProperty.data,
        )
        .outerjoin(UrlCheck, UrlCheck.url_id == Url.id)
        .outerjoin(Check, UrlCheck.check_id == Check.id)
        .outerjoin(
            UrlProperty,
            and_(UrlProperty.url_id == Url.id, UrlProperty.check_id == Check.id),
        )
        .outerjoin(Property, Property.id == UrlProperty.property_id)
        .where(Url.id == pk)
        .order_by(desc(Check.id), Property.id)
    )

    if "check" in request.args:
        check_id = request.args.get("check", type=int)
        urls_stmt = urls_stmt.filter(
            Check.id == check_id, UrlProperty.check_id == check_id
        )
    print(urls_stmt)
    url_data = urls_stmt.all()

    if not url_data:
        abort(404)

    return render_template("core/url.html", urls=url_data)


@bp.route("/dataframe/<pk>/")
def dataframe(pk):
    df = Dataframe.query.get_or_404(pk)
    per_page = request.args.get(
        "per_page", current_app.config["URLS_PER_PAGE"], type=int
    )

    check_id = None
    check = None
    is_checking = None
    is_extracting_data = None
    # TODO check connection - disable checking if connection error
    if df.checks:
        check_id = request.args.get(
            "check",
            df.active_check.id if df.active_check else df.checks[0].id,
            type=int,
        )
        check = db.session.get(Check, check_id)
        try:
            is_checking = check.is_checking()
            is_extracting_data = check.is_extracting_data()
        except (ConnectionError, ResponseError) as e:
            current_app.logger.warning(
                f"Queue server is unavailable. {e}", exc_info=True
            )
            flash("Сервер задач не отвечает.", "error")
        except NoSuchJobError:
            # no task queued for the check
            pass
        except AttributeError:
            # check is None
            flash(f"Проверка {check_id} не найдена.", "warning")

    urls = (
        db.session.query(
            Url.id,
            Url.url,
            UrlCheck.status,
            func.count(UrlProperty.url_id).label("is_handled"),
        )
        .group_by(Url.id, Url.url, UrlCheck.status)
        .outerjoin(Url.checks.and_(UrlCheck.check_id == check_id))
        .outerjoin(
            UrlProperty,
            and_(UrlProperty.url_id == Url.id, UrlProperty.check_id == check_id),
        )
        .filter(Url.dataframe_id == df.id)
        .order_by(UrlCheck.status.desc(), desc("is_handled"))
    )

    urls = urls.paginate(per_page=per_page)

    return render_template(
        "core/dataframe.html",
        dataframe=df,
        check=check,
        is_extracting_data=is_extracting_data,
        is_checking=is_checking,
        urls=urls,
    )


@bp.route("/dataframe/add/", methods=["GET", "POST"])
def dataframe_add():
    form = DataFrameForm()

    if form.validate_on_submit():
        df = Dataframe(name=form.name.data, description=form.description.data)
        db.session.add(df)
        db.session.commit()

        if form.urls.data:
            url_list = text_to_list(form.urls.data)
            urls = [{"dataframe_id": df.id, "url": url} for url in url_list]
            stmt = insert(Url)
            db.session.execute(stmt, urls)
            db.session.commit()

        flash("Датафрейм добавлен.")

        return redirect(url_for("core.dataframe", pk=df.id))

    return render_template(
        "core/dataframe_add.html", title="Добавить датафрейм", form=form
    )


@bp.route("/dataframe/<pk>/edit/", methods=["GET", "POST"])
def dataframe_edit(pk):
    df = Dataframe.query.get_or_404(pk)
    # If there is a dataframe check - add a response status for checked urls if exists
    # else just show dataframe urls
    if df.checks:
        check_id = request.args.get("check", df.checks[0].id, type=int)
    else:
        check_id = None

    urls = (
        db.session.query(Url.id, Url.url, UrlCheck.status)
        .outerjoin(Url.checks.and_(UrlCheck.check_id == check_id))
        .filter(Url.dataframe == df)
        .order_by(UrlCheck.status.desc())
    )

    form = DataFrameForm(obj=df)
    # fill the form with url lines
    if request.method == "GET":
        # show url status and/or url
        form.urls.data = "\r\n".join(
            [
                str(url.status) + " " + url.url if check_id and url.status else url.url
                for url in urls
            ]
        )

    if form.validate_on_submit():
        new_urls = set(text_to_list(form.urls.data))

        # save urls field to a list and delete it from the form to avoid direct saving
        del form.urls
        form.populate_obj(df)

        # find same urls for old and new urls that won't be changed
        del_url_ids = set()
        for url in urls:
            if url.url in new_urls:
                new_urls.remove(url.url)
            else:
                del_url_ids.add(url.id)
        # bulk delete - urls are in urls from db and not in new_urls
        if del_url_ids:
            # TODO check if related tables are also deleted
            db.session.execute(Url.__table__.delete().where(Url.id.in_(del_url_ids)))
        # db.session.execute(delete(Url).where(Url.id.in_(del_urls)))

        # insert new urls - urls are in new_urls and not in old_urls
        if new_urls:
            db.session.execute(
                Url.__table__.insert(),
                [{"url": url, "dataframe_id": df.id} for url in new_urls],
            )
        # db.session.add_all([Url(dataframe=df, url=url) for url in new_urls])
        # db.session.execute(insert(Url),
        # [{'url': url, 'dataframe_id': df.id} for url in new_urls])

        db.session.commit()

        flash("Датафрейм изменён.")

        return redirect(url_for("core.dataframe", pk=df.id))

    return render_template(
        "core/dataframe_edit.html", title="Изменить датафрейм", form=form
    )


@bp.route("/dataframe/<pk>/delete/", methods=["GET", "POST"])
def dataframe_delete(pk):
    # TODO check running tasks of dataframe's checks before deleting?
    df = Dataframe.query.get_or_404(pk)
    form = EmptyForm()
    form.button.label.text = "Удалить"

    if form.validate_on_submit():
        db.session.delete(df)
        db.session.commit()

        flash(f'Датафрейм "{df.name}" удалён.')

        return redirect(url_for("core.index"))

    return render_template(
        "core/delete.html",
        title=f'Удалить датафрейм "{df.name}" ?',
        description=df.description,
        form=form,
    )


def run_dataframe_check(check: Check) -> dict:
    # Check if a message broker is available
    try:
        if job := check.start():
            current_app.logger.info(
                f'Task "check_dataframe" has been launched. Task id: {job.get_id()}'
            )
        else:
            current_app.logger.info(
                'Task "check_dataframe" has not been launched. '
                "Something wrong with check.start"
            )
    except (ConnectionError, ResponseError) as e:
        current_app.logger.error(
            f'Task "check_dataframe" has not been launched. Error: {e}'
        )
        return {
            "status": False,
            "message": f'Ошибка запуска проверки "{check.name}". '
            f"Сервер задач не отвечает.",
        }
    except Exception as e:
        current_app.logger.error(
            f'Task "check_dataframe" has not been launched. Error: {e}'
        )
        return {
            "status": False,
            "message": f'Ошибка запуска проверки "{check.name}". Неизвестная ошибка.',
        }
    else:
        return {
            "status": True,
            "message": f'Проверка "{check.name}" датафрейма "{check.dataframe.name}" '
            f"запущена.",
        }


@bp.route("/dataframe/<pk>/check/", methods=["GET", "POST"])
def dataframe_check(pk):
    # TODO check start frequency - do not start if prev check has start_time
    #  less than ... ?
    df = Dataframe.query.get_or_404(pk)

    # check if dataframe is currently being checked
    # TODO change to check.is_checking - get current job's status at a queue by job_id ?
    cur_check = (
        db.session.query(Check.id).filter_by(dataframe=df, end_time=None).first()
        is not None
    )
    if cur_check:
        flash("Датафрейм уже проверяется.")
        return redirect(url_for("core.dataframe", pk=df.id))

    form = DataFrameCheckForm()
    # fill default name with current date time
    if request.method == "GET":
        form.name.data = datetime.now().strftime("%Y-%m-%d %H:%M")

    if form.validate_on_submit():
        check = Check(dataframe=df, name=form.name.data)
        db.session.add(check)
        db.session.commit()

        result = run_dataframe_check(check)
        flash(result["message"])

        if not result["status"]:
            db.session.delete(check)
            db.session.commit()
            return redirect(url_for("core.dataframe", pk=df.id))

        return redirect(url_for("core.dataframe", pk=df.id, check=check.id))

    return render_template(
        "core/dataframe_check.html",
        dataframe=df,
        form=form,
        title=f'Запустить проверку датафрейма "{df.name}" ?',
    )


@bp.route("/check/<pk>/recheck/")
def dataframe_check_new(pk):
    check = Check.query.get_or_404(pk)

    if check.is_checking():
        flash("Датафрейм уже проверяется.")
        return redirect(
            url_for("core.dataframe", pk=check.dataframe_id, check=check.id)
        )

    result = run_dataframe_check(check)

    flash(result["message"])

    return redirect(url_for("core.dataframe", pk=check.dataframe_id, check=check.id))


@bp.route("/check/<pk>/edit/", methods=["GET", "POST"])
def check_edit(pk):
    check = Check.query.get_or_404(pk)

    form = DataFrameCheckForm(obj=check)
    form.submit.label.text = "Сохранить"

    if form.validate_on_submit():
        form.populate_obj(check)
        db.session.commit()
        flash(f"Проверка {check.name} изменена.")

        return redirect(url_for("core.dataframe", pk=check.dataframe.id))

    return render_template(
        "core/dataframe_check.html",
        dataframe=check.dataframe,
        form=form,
        title=f'Изменить проверку "{check.name}" ?',
    )


@bp.route("/check/<pk>/delete/", methods=["GET", "POST"])
def check_delete(pk):
    # TODO memmory error ? Make step by step deleting or use worker
    check = Check.query.get_or_404(pk)
    df = check.dataframe

    form = EmptyForm()
    form.button.label.text = "Удалить"

    if form.validate_on_submit():
        try:
            if check.is_checking():
                check.stop_extract_data()

            if check.is_checking():
                check.stop()
        except (ConnectionError, ResponseError) as e:
            current_app.logger.warning(
                f"Queue server is unavailable. {e}", exc_info=True
            )
        except NoSuchJobError:
            # no task queued for the check
            pass

        db.session.delete(check)
        db.session.commit()

        return redirect(url_for("core.dataframe", pk=df.id))

    description = str(check.start_time) + " - " + str(check.end_time)

    return render_template(
        "core/delete.html",
        title=f'Удалить проверку "{check.name}" ?',
        description=description,
        form=form,
    )


@bp.route("/check/<pk>/extract/")
def check_extract_data(pk):
    check = Check.query.get_or_404(pk)

    if not check.dataframe.properties:
        flash("Перед извлечением данных заполните селекторы датафрейма.")
        return redirect(url_for("core.dataframe_selectors", pk=check.dataframe.id))

    # extracting selectors test
    if url_limit := request.args.get("test", type=int):
        msg = get_check_test_msg(check.id, url_limit)
        flash(msg)

        return redirect(
            url_for("core.dataframe", pk=check.dataframe_id, check=check.id)
        )

    if check.is_extracting_data():
        flash(f'Обработка данных проверки "{check.name}" уже идёт.')
        return redirect(
            url_for("core.dataframe", pk=check.dataframe_id, check=check.id)
        )

    # check weather we extract all data or only new
    kwargs = {}
    only_new = request.args.get("only_new", type=int)
    if only_new is not None:
        kwargs["only_new"] = bool(only_new)

    try:
        job = check.extract_data(**kwargs)
        flash(f'Обработка данных проверки "{check.name}" запущена.')
        current_app.logger.info(
            f'Task "check_extract_data" has launched. Task id: {job.get_id()}'
        )
    except (ConnectionError, ResponseError) as e:
        current_app.logger.error(
            f'Task "check_extract_data" has not launched. Error: {e}'
        )
        flash(f'Ошибка запуска проверки "{check.name}". Сервер задач не отвечает.')

    return redirect(url_for("core.dataframe", pk=check.dataframe_id, check=check.id))


def get_check_test_msg(check_id: int, url_limit: int = None) -> str:
    properties = {prop.id: prop.name for prop in Property.query}

    df_id = db.session.query(Check.dataframe_id).filter_by(id=check_id).scalar()
    df_properties = get_dataframe_selectors(df_id)

    checked_urls = get_checked_urls_with_url_stmt(check_id, False, url_limit)
    checked_urls_data = get_urls_data_by_selectors(
        checked_urls, df_properties, properties
    )

    msg = get_msg_for_checked_urls(checked_urls_data)

    return msg


def get_urls_data_by_selectors(
    urls: list, selectors: dict[int, str], properties: dict[int:str]
) -> dict[str, dict]:
    urls_data = {}

    for url_check in urls:
        url_url = src.models.Url.url
        parsed_data = parse_data_by_xpath(url_check.raw_data, selectors)
        url_data = {}
        for prop_id, prop_value in parsed_data.items():
            # replace property id with a name of the property as a key
            url_data[properties[prop_id]] = prop_value

        urls_data[url_url] = url_data

    return urls_data


def get_checked_urls_with_url_stmt(*args, **kwargs):
    checked_urls = get_checked_urls_stmt(*args, **kwargs).subquery()

    return db.session.query(Url, checked_urls).join(
        checked_urls, Url.id == checked_urls.c.url_id
    )


def get_msg_for_checked_urls(urls: dict) -> str:
    msg = ""
    for url_url, url_data in urls.items():
        msg += url_url + "<br/>"
        for prop_id, prop_value in url_data.items():
            # msg += prop_id + ':' + ' '.join(prop_value) + ', '
            msg += prop_id + ":" + prop_value + ", "

        msg = msg[:~1]
        msg += "<br/>"

    return msg


@bp.route("/check/<pk>/activate/")
def check_activate(pk):
    # makes current check active for its dataframe
    check = Check.query.get_or_404(pk)
    check.dataframe.check_id = check.id
    db.session.commit()

    flash(f"Проверка {check}  активирована для датафрейма {check.dataframe}.")
    return redirect(url_for("core.dataframe", pk=check.dataframe_id, check=check.id))


@bp.route("/check/<pk>/stop/")
def check_stop(pk):
    check = Check.query.get_or_404(pk)

    # stop a certain job or both
    stop_param = "job"
    stop_job = request.args.get(stop_param)

    try:
        if stop_job == "extract" or stop_job is None:
            check.stop_extract_data()
            flash("Остановлено извлечение данных.")

        if stop_job == "check" or stop_job is None:
            check.stop()
            flash("Остановлено получение данных.")
    except (ConnectionError, ResponseError) as e:
        current_app.logger.warning(
            f"Can not stop check {check}. Queue server is unavailable. {e}",
            exc_info=True,
        )
        flash("Сервер задач не отвечает. Попробуйте позже.")
    except NoSuchJobError as e:
        # no task queued for the check
        current_app.logger.warning(
            f"Can not stop check {check}. No such job. {e}", exc_info=True
        )
        flash("Задача не найдена.")

    return redirect(url_for("core.dataframe", pk=check.dataframe_id, check=check.id))


@bp.route("/cluster/<pk>/", methods=["GET", "POST"])
def cluster(pk):
    clr = Cluster.query.get_or_404(pk)

    form = ClusterForm(obj=clr, parent_id="3")
    # fill parent field
    # TODO check out all descendants
    query = Cluster.query.filter(
        (Cluster.id != pk) & ((Cluster.parent_id != pk) | (Cluster.parent_id.is_(None)))
    ).all()
    choices = [(item.id, item.name) for item in query]
    choices.insert(0, (0, ""))
    form.parent_id.choices = choices

    current_frames = [df.name for df in clr.dataframes]
    # fill dataframes field
    query = Dataframe.query.with_entities(Dataframe.id, Dataframe.name)
    form.frames.choices = [(df.name, df.name) for df in query]

    if form.validate_on_submit():
        if not form.parent_id.data:
            form.parent_id.data = None

        populate_object(clr, form, exclude=["frames"])

        # if dataframes changed - delete previous and append new
        if form.frames.data != current_frames:
            dataframes_for_del = set(current_frames) - set(form.frames.data)
            dataframes_for_add = set(form.frames.data) - set(current_frames)

            if dataframes_for_del:
                # delete from m2m table dataframe ids where select ids with names
                # for deleting
                db.session.execute(
                    DataframeCluster.delete().where(
                        DataframeCluster.c.cluster_id == clr.id,
                        DataframeCluster.c.dataframe_id.in_(
                            Dataframe.query.with_entities(Dataframe.id).filter(
                                Dataframe.name.in_(dataframes_for_del)
                            )
                        ),
                    )
                )
            if dataframes_for_add:
                dataframes_for_add_ids = Dataframe.query.with_entities(
                    Dataframe.id
                ).filter(Dataframe.name.in_(dataframes_for_add))
                db.session.execute(
                    DataframeCluster.insert(),
                    [
                        {"cluster_id": clr.id, "dataframe_id": df_id}
                        for (df_id,) in dataframes_for_add_ids
                    ],
                )

        db.session.commit()

        flash("Кластер обновлён.")

    return render_template("core/cluster.html", cluster=clr, form=form)


@bp.route("/cluster/add/", methods=["GET", "POST"])
def cluster_add():
    form = ClusterAddForm()
    # fill up parent cluster select field
    query = Cluster.query.all()
    choices = [(item.id, item.name) for item in query]
    choices.insert(0, (0, ""))
    form.parent_id.choices = choices

    if form.validate_on_submit():
        clr = Cluster(
            name=form.name.data,
            title=form.title.data,
            description=form.description.data,
            excerpt=form.excerpt.data,
            text=form.text.data,
            image=form.image.data,
        )

        if form.parent_id.data:
            clr.parent_id = form.parent_id.data

        db.session.add(clr)
        db.session.commit()

        flash("Кластер добавлен.")

        return redirect(url_for("core.cluster", pk=clr.id))

    return render_template("core/cluster_add.html", title="Добавить кластер", form=form)


@bp.route("/cluster/<pk>/delete/", methods=["GET", "POST"])
def cluster_delete(pk):
    clr = Cluster.query.get_or_404(pk)

    form = EmptyForm()
    form.button.label.text = "Удалить"

    if form.validate_on_submit():
        db.session.delete(clr)
        db.session.commit()
        flash(f'Кластер "{clr.name}" удалён.')

        return redirect(url_for("core.index"))

    return render_template(
        "core/delete.html",
        title=f'Удалить кластер "{clr.name}" и всех его потомков?',
        form=form,
    )
