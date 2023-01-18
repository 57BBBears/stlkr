from flask import Blueprint, render_template, url_for, redirect, flash, request, current_app
from app.forms import DataFrameForm, EmptyForm, DataFrameCheckForm, ClusterForm, ClusterAddForm
from app.models import DataFrame, Url, Check, UrlCheck, Cluster
from app.utils import text_to_list
from app import db
from datetime import datetime
from redis.exceptions import ResponseError
from app.utils import populate_object

bp = Blueprint('routes', __name__)


@bp.route('/')
def index():
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    df = DataFrame.query.order_by(DataFrame.id).paginate(per_page=per_page)
    clusters = Cluster.query.order_by(Cluster.id)

    return render_template('index.html', title='Главная', dataframes=df, clusters=clusters)


@bp.route('/dataframe/<pk>/')
def dataframe(pk):
    df = DataFrame.query.get_or_404(pk)
    per_page = request.args.get('per_page', current_app.config['URLS_PER_PAGE'], type=int)

    if df.checks:
        check_id = request.args.get('check', df.checks[0].id, type=int)
    else:
        check_id = None

    urls = db.session.query(Url.url, UrlCheck.status)\
        .outerjoin(Url.checks.and_(UrlCheck.check_id == check_id))\
        .filter((Url.dataframe_id == df.id))\
        .order_by(UrlCheck.status.desc())

    urls = urls.paginate(per_page=per_page)

    return render_template('dataframe.html', dataframe=df, check_id=check_id, urls=urls)


@bp.route('/dataframe/add/', methods=['GET', 'POST'])
def dataframe_add():
    form = DataFrameForm()

    if form.validate_on_submit():
        df = DataFrame(name=form.name.data, description=form.description.data)
        db.session.add(df)
        db.session.commit()

        if form.urls.data:
            url_list = text_to_list(form.urls.data)
            urls = [{'dataframe_id': df.id, 'url': url} for url in url_list]
            db.session.execute(Url.__table__.insert(urls))
            db.session.commit()

        flash('Датафрейм добавлен.')

        return redirect(url_for('routes.dataframe', pk=df.id))

    return render_template('dataframe_add.html', title='Добавить датафрейм', form=form)


@bp.route('/dataframe/<pk>/edit/', methods=['GET', 'POST'])
def dataframe_edit(pk):
    df = DataFrame.query.get_or_404(pk)
    if df.checks:
        check_id = request.args.get('check', df.checks[0].id, type=int)
    else:
        check_id = None
    # If there is a dataframe check - add a response status for checked urls if exists else just show dataframe urls

    urls = db.session.query(Url.id, Url.url, UrlCheck.status)\
        .outerjoin(Url.checks.and_(UrlCheck.check_id == check_id))\
        .filter(Url.dataframe == df)\
        .order_by(UrlCheck.status.desc())

    form = DataFrameForm(obj=df)
    # fill the form with url lines
    if request.method == 'GET':
        # show url status and/or url
        form.urls.data = '\r\n'.join(
            [str(url.status) + ' ' + url.url if check_id and url.status else url.url for url in urls]
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
        #db.session.execute(delete(Url).where(Url.id.in_(del_urls)))

        # insert new urls - urls are in new_urls and not in old_urls
        if new_urls:
            db.session.execute(Url.__table__.insert(), [{'url': url, 'dataframe_id': df.id} for url in new_urls])
        #db.session.add_all([Url(dataframe=df, url=url) for url in new_urls])
        #db.session.execute(insert(Url), [{'url': url, 'dataframe_id': df.id} for url in new_urls])

        db.session.commit()

        flash('Датафрейм изменён.')

        return redirect(url_for('routes.dataframe', pk=df.id))

    return render_template('dataframe_edit.html', title='Изменить датафрейм', form=form)


@bp.route('/dataframe/<pk>/delete/', methods=['GET', 'POST'])
def dataframe_delete(pk):
    df = DataFrame.query.get_or_404(pk)
    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        db.session.delete(df)
        db.session.commit()

        flash(f'Датафрейм "{df.name}" удалён.')

        return redirect(url_for('routes.index'))

    return render_template('delete.html', title=f'Удалить датафрейм "{df.name}" ?', description=df.description, form=form)


@bp.route('/dataframe/<pk>/check/', methods=['GET', 'POST'])
def dataframe_check(pk):
    # TODO check start frequency - do not start if prev check has start_time less than ...
    df = DataFrame.query.get_or_404(pk)

    # check if dataframe is currently being checked
    # TODO change to check.is_checking - get current job's status at a queue by job_id ?
    cur_check = db.session.query(Check.id).filter_by(dataframe=df, end_time=None).first() is not None
    if cur_check:
        flash('Датафрейм уже проверяется.')
        return redirect(url_for('routes.dataframe', pk=df.id))

    form = DataFrameCheckForm()
    # fill default name with current date time
    if request.method == 'GET':
        form.name.data = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    if form.validate_on_submit():
        check = Check(dataframe=df, name=form.name.data, selectors=form.name.data)
        db.session.add(check)
        db.session.commit()
        # Check if a message broker is available
        try:
            if job := check.start():
                current_app.logger.info(f'Task "check_dataframe" has launched. Task id: {job.get_id()}')
            else:
                current_app.logger.info(f'Task "check_dataframe" has not launched. Something wrong with check.start')
        except ResponseError as e:
            current_app.logger.error(f'Task "check_dataframe" has not launched. Error: ', e)
            db.session.delete(check)
            db.session.commit()
            flash(f'Ошибка запуска проверки "{form.name.data}". Сервер задач не отвечает.')
        else:
            flash(f'Проверка "{form.name.data}" датафрейма "{df.name}" запущена.')

        return redirect(url_for('routes.dataframe', pk=df.id))

    return render_template('dataframe_check.html',
                           title=f'Запустить проверку датафрейма "{df.name}" ?', dataframe=df, form=form)


@bp.route('/check/<pk>/edit/', methods=['GET', 'POST'])
def check_edit(pk):
    check = Check.query.get_or_404(pk)

    form = DataFrameCheckForm(obj=check)

    if form.validate_on_submit():
        form.populate_obj(check)
        check.save()
        flash(f'Проверка {check.name} изменена.')

        return redirect(url_for('routes.dataframe', pk=check.dataframe.id))

    return render_template('dataframe_check.html', title=f'Изменить проверку "{check.name}" ?')


@bp.route('/check/<pk>/delete/', methods=['GET', 'POST'])
def check_delete(pk):
    check = Check.query.get_or_404(pk)
    df = check.dataframe

    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        # TODO check if check has a running task - stop it first
        db.session.delete(check)
        db.session.commit()

        return redirect(url_for('routes.dataframe', pk=df.id))

    description = str(check.start_time) + ' - ' + str(check.end_time)

    return render_template('delete.html', title=f'Удалить проверку "{check.name}" ?', description=description, form=form)


@bp.route('/check/<pk>/extract_data/')
def check_extract_data(pk):
    check = Check.query.get_or_404(pk)

    if not check.selectors:
        flash(f'Заполните селекторы проверки "{check.name}".')
        return redirect(url_for('routes.check_edit', pk=check.id))

    try:
        if job := check.extract_data():
            flash(f'Обработка данных проверки "{check.name}" запущена.')
            current_app.logger.info(f'Task "check_extract_data" has launched. Task id: {job.get_id()}')
        else:
            flash(f'Обработка данных проверки "{check.name}" уже идёт.')
    except ResponseError as e:
        current_app.logger.error('Task "check_extract_data" has not launched. ', e)
        flash(f'Ошибка запуска проверки "{check.name}". Сервер задач не отвечает.')

    return redirect(url_for('routes.dataframe', pk=check.dataframe.id))


@bp.route('/cluster/<pk>/', methods=['GET', 'POST'])
def cluster(pk):
    clr = Cluster.query.get_or_404(pk)
    # TODO check out all descendants
    query = Cluster.query.filter((Cluster.id != pk) & ((Cluster.parent_id != pk) | (Cluster.parent_id == None))).all()
    choices = [(item.id, item.name) for item in query]
    choices.insert(0, (0, ''))

    form = ClusterForm(obj=clr)
    form.parent_id.choices = choices

    query = DataFrame.query.with_entities(DataFrame.id, DataFrame.name)
    form.frames.choices = [(df.id, df.name) for df in query]
    #form.frames.choices = DataFrame.query.all()
    #current_app.logger.info(form._fields)
    if form.validate_on_submit():
        if not form.parent_id.data:
            form.parent_id.data = None

        populate_object(clr, form, exclude=['frames'])
        #clr.dataframes =
        #form.populate_obj(clr)
        db.session.commit()

        flash('Кластер обновлён.')

    return render_template('cluster.html', cluster=clr, form=form)


@bp.route('/cluster/add/', methods=['GET', 'POST'])
def cluster_add():
    form = ClusterAddForm()
    # fill up parent cluster select field
    query = Cluster.query.all()
    choices = [(item.id, item.name) for item in query]
    choices.insert(0, (0, ''))
    form.parent_id.choices = choices

    if form.validate_on_submit():
        clr = Cluster(name=form.name.data,
                      title=form.title.data,
                      description=form.description.data,
                      excerpt=form.excerpt.data,
                      text=form.text.data,
                      image=form.image.data)

        if form.parent_id.data:
            clr.parent_id = form.parent_id.data

        db.session.add(clr)
        db.session.commit()

        flash('Кластер добавлен.')

        return redirect(url_for('routes.cluster', pk=clr.id))

    return render_template('cluster_add.html', title='Добавить кластер', form=form)


@bp.route('/cluster/<pk>/delete/', methods=['GET', 'POST'])
def cluster_delete(pk):
    clr = Cluster.query.get_or_404(pk)

    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        db.session.delete(clr)
        db.session.commit()
        flash(f'Кластер "{clr.name}" удалён.')

        return redirect(url_for('routes.index'))

    return render_template('delete.html', title=f'Удалить кластер "{clr.name}" и всех его потомков?', form=form)