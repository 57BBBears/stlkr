import json
from flask import render_template, url_for, redirect, flash, request, current_app
from app.core.models import DataFrame, Url, Check, UrlCheck, Cluster, DataFrameCluster
from app.core.utils import text_to_list
from app import db
from datetime import datetime
from redis.exceptions import ConnectionError, ResponseError
from rq.exceptions import NoSuchJobError
from app.core.utils import populate_object
from app.core import bp
from app.core.forms import DataFrameForm, EmptyForm, DataFrameCheckForm, ClusterForm, ClusterAddForm
from app.core.tasks import parse_data_by_xpath


@bp.route('/')
def index():
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    df = DataFrame.query.order_by(DataFrame.id).paginate(per_page=per_page)
    clusters = Cluster.query.order_by(Cluster.id)

    return render_template('core/index.html', title='Админка', dataframes=df, clusters=clusters)


@bp.route('/dataframe/<pk>/')
def dataframe(pk):
    df = DataFrame.query.get_or_404(pk)
    per_page = request.args.get('per_page', current_app.config['URLS_PER_PAGE'], type=int)

    check_id = None
    check = None
    is_checking = None
    is_extracting_data = None
    # TODO check connection - disable checking if connection error
    if df.checks:
        check_id = request.args.get('check', df.checks[0].id, type=int)
        check = db.session.get(Check, check_id)
        try:
            is_checking = check.is_checking()
            is_extracting_data = check.is_extracting_data()
        except (ConnectionError, ResponseError) as e:
            current_app.logger.warning(f'Queue server is unavailable. {e}', exc_info=True)
            flash('Сервер задач не отвечает.', 'error')
        except NoSuchJobError:
            # no task queued for the check
            pass
        except AttributeError:
            # check is None
            flash(f'Проверка {check_id} не найдена.', 'warning')

    urls = db.session.query(Url.url, UrlCheck.status)\
        .outerjoin(Url.checks.and_(UrlCheck.check_id == check_id))\
        .filter((Url.dataframe_id == df.id))\
        .order_by(UrlCheck.status.desc())

    urls = urls.paginate(per_page=per_page)

    return render_template('core/dataframe.html', dataframe=df, check=check,
                           is_extracting_data=is_extracting_data, is_checking=is_checking, urls=urls)


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

        return redirect(url_for('core.dataframe', pk=df.id))

    return render_template('core/dataframe_add.html', title='Добавить датафрейм', form=form)


@bp.route('/dataframe/<pk>/edit/', methods=['GET', 'POST'])
def dataframe_edit(pk):
    df = DataFrame.query.get_or_404(pk)
    # If there is a dataframe check - add a response status for checked urls if exists else just show dataframe urls
    if df.checks:
        check_id = request.args.get('check', df.checks[0].id, type=int)
    else:
        check_id = None

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

        return redirect(url_for('core.dataframe', pk=df.id))

    return render_template('core/dataframe_edit.html', title='Изменить датафрейм', form=form)


@bp.route('/dataframe/<pk>/delete/', methods=['GET', 'POST'])
def dataframe_delete(pk):
    #TODO check running tasks of dataframe's checks before deleting?
    df = DataFrame.query.get_or_404(pk)
    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        db.session.delete(df)
        db.session.commit()

        flash(f'Датафрейм "{df.name}" удалён.')

        return redirect(url_for('core.index'))

    return render_template('core/delete.html', title=f'Удалить датафрейм "{df.name}" ?', description=df.description, form=form)


@bp.route('/dataframe/<pk>/check/', methods=['GET', 'POST'])
def dataframe_check(pk):
    # TODO check start frequency - do not start if prev check has start_time less than ... ?
    df = DataFrame.query.get_or_404(pk)

    # check if dataframe is currently being checked
    # TODO change to check.is_checking - get current job's status at a queue by job_id ?
    cur_check = db.session.query(Check.id).filter_by(dataframe=df, end_time=None).first() is not None
    if cur_check:
        flash('Датафрейм уже проверяется.')
        return redirect(url_for('core.dataframe', pk=df.id))

    form = DataFrameCheckForm()
    # fill default name with current date time
    if request.method == 'GET':
        form.name.data = datetime.now().strftime('%Y-%m-%d %H:%M')

    if form.validate_on_submit():
        check = Check(dataframe=df, name=form.name.data, selectors=form.selectors.data)
        db.session.add(check)
        db.session.commit()
        # Check if a message broker is available
        try:
            if job := check.start():
                current_app.logger.info(f'Task "check_dataframe" has been launched. Task id: {job.get_id()}')
            else:
                current_app.logger.info(f'Task "check_dataframe" has not been launched. Something wrong with check.start')
        except (ConnectionError, ResponseError) as e:
            current_app.logger.error(f'Task "check_dataframe" has not been launched. Error: {e}')
            db.session.delete(check)
            db.session.commit()
            flash(f'Ошибка запуска проверки "{form.name.data}". Сервер задач не отвечает.')
        except Exception as e:
            current_app.logger.error(f'Task "check_dataframe" has not been launched. Error: {e}')
            db.session.delete(check)
            db.session.commit()
            flash(f'Ошибка запуска проверки "{form.name.data}". Неизвестная ошибка.')
        else:
            flash(f'Проверка "{form.name.data}" датафрейма "{df.name}" запущена.')

        return redirect(url_for('core.dataframe', pk=df.id))

    return render_template('core/dataframe_check.html', dataframe=df, form=form,
                           title=f'Запустить проверку датафрейма "{df.name}" ?')


@bp.route('/check/<pk>/edit/', methods=['GET', 'POST'])
def check_edit(pk):
    check = Check.query.get_or_404(pk)

    form = DataFrameCheckForm(obj=check)

    if form.validate_on_submit():
        form.populate_obj(check)
        db.session.commit()
        flash(f'Проверка {check.name} изменена.')

        return redirect(url_for('core.dataframe', pk=check.dataframe.id))

    return render_template('core/dataframe_check.html', dataframe=check.dataframe, form=form,
                           title=f'Изменить проверку "{check.name}" ?')


@bp.route('/check/<pk>/delete/', methods=['GET', 'POST'])
def check_delete(pk):
    check = Check.query.get_or_404(pk)
    df = check.dataframe

    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        try:
            check.stop_extract_data()
            check.stop()
        except (ConnectionError, ResponseError) as e:
            current_app.logger.warning(f'Queue server is unavailable. {e}', exc_info=True)
        except NoSuchJobError:
            #no task queued for the check
            pass

        db.session.delete(check)
        db.session.commit()

        return redirect(url_for('core.dataframe', pk=df.id))

    description = str(check.start_time) + ' - ' + str(check.end_time)

    return render_template('core/delete.html', title=f'Удалить проверку "{check.name}" ?', description=description, form=form)


@bp.route('/check/<pk>/extract_data/')
def check_extract_data(pk):
    check = Check.query.get_or_404(pk)

    if not check.selectors:
        flash(f'Заполните селекторы проверки "{check.name}".')
        return redirect(url_for('core.check_edit', pk=check.id))

    # test selectors
    if 'test' in request.args:
        data = check_test_selectors(check, check.selectors)
        flash(data)

        return redirect(url_for('core.dataframe', pk=check.dataframe_id, check=check.id))

    if check.is_extracting_data():
        flash(f'Обработка данных проверки "{check.name}" уже идёт.')
        return redirect(url_for('core.dataframe', pk=check.dataframe_id, check=check.id))

    # check weather we extract all data or only new
    kwargs = {}
    only_new = request.args.get('only_new', type=int)
    if only_new is not None:
        kwargs['only_new'] = bool(only_new)

    try:
        job = check.extract_data(**kwargs)
        flash(f'Обработка данных проверки "{check.name}" запущена.')
        current_app.logger.info(f'Task "check_extract_data" has launched. Task id: {job.get_id()}')
    except (ConnectionError, ResponseError) as e:
        current_app.logger.error(f'Task "check_extract_data" has not launched. Error: {e}')
        flash(f'Ошибка запуска проверки "{check.name}". Сервер задач не отвечает.')

    return redirect(url_for('core.dataframe', pk=check.dataframe_id, check=check.id))

def check_test_selectors(check: Check, selectors: str) -> str:
    url_check = UrlCheck.query.filter(UrlCheck.raw_data.isnot(None), UrlCheck.check==check, UrlCheck.status==200).first()
    if url_check:
        source = url_check.raw_data
        try:
            selectors_dict = json.loads(check.selectors)
        except json.JSONDecodeError:
            return 'Ошибка JSON декодирования селекторов.'
        else:
            data = parse_data_by_xpath(source, selectors_dict)
    else:
        return 'Нет данных для проверки.'

    return data

@bp.route('/check/<pk>/activate/')
def check_activate(pk):
    # makes current check active for its dataframe
    check = Check.query.get_or_404(pk)
    check.dataframe.check_id = check.id
    db.session.commit()

    flash(f'Проверка {check}  активирована для датафрейма {check.dataframe}.')
    return redirect(url_for('core.dataframe', pk=check.dataframe_id, check=check.id))


@bp.route('/check/<pk>/stop/')
def check_stop(pk):
    check = Check.query.get_or_404(pk)

    # stop certain job or both
    stop_param = 'job'
    stop_job = request.args.get(stop_param)

    try:
        if stop_job == 'extract' or stop_job is None:
            check.stop_extract_data()
            flash('Остановлено извлечение данных.')

        if stop_job == 'check' or stop_job is None:
            check.stop()
            flash('Остановлено получение данных.')
    except (ConnectionError, ResponseError) as e:
        current_app.logger.warning(f'Can not stop check {check}. Queue server is unavailable. {e}', exc_info=True)
        flash('Сервер задач не отвечает. Попробуйте позже.')
    except NoSuchJobError as e:
        # no task queued for the check
        current_app.logger.warning(f'Can not stop check {check}. No such job. {e}', exc_info=True)
        flash('Задача не найдена.')

    return redirect(url_for('core.dataframe', pk=check.dataframe_id, check=check.id))


@bp.route('/cluster/<pk>/', methods=['GET', 'POST'])
def cluster(pk):
    clr = Cluster.query.get_or_404(pk)

    form = ClusterForm(obj=clr, parent_id='3')
    # fill parent field
    # TODO check out all descendants
    query = Cluster.query.filter(
        (Cluster.id != pk) & ((Cluster.parent_id != pk) | (Cluster.parent_id.is_(None)))).all()
    choices = [(item.id, item.name) for item in query]
    choices.insert(0, (0, ''))
    form.parent_id.choices = choices

    current_frames = [df.name for df in clr.dataframes]
    # fill dataframes field
    query = DataFrame.query.with_entities(DataFrame.id, DataFrame.name)
    form.frames.choices = [(df.name, df.name) for df in query]


    if form.validate_on_submit():
        if not form.parent_id.data:
            form.parent_id.data = None

        populate_object(clr, form, exclude=['frames'])

        # if dataframes changed - delete previous and append new
        if form.frames.data != current_frames:
            dataframes_for_del = set(current_frames) - set(form.frames.data)
            dataframes_for_add = set(form.frames.data) - set(current_frames)

            if dataframes_for_del:
                # delete from m2m table dataframe ids where select ids with names for deleting
                db.session.execute(DataFrameCluster.delete().
                                   where(DataFrameCluster.c.cluster_id == clr.id,
                                         DataFrameCluster.c.dataframe_id.in_(
                                             DataFrame.query.with_entities(DataFrame.id).filter(
                                                 DataFrame.name.in_(dataframes_for_del)
                                             )
                                         )
                                         )
                                   )
            if dataframes_for_add:
                dataframes_for_add_ids = DataFrame.query.with_entities(DataFrame.id).filter(
                                                 DataFrame.name.in_(dataframes_for_add)
                                             )
                db.session.execute(DataFrameCluster.insert(),
                                   [{'cluster_id': clr.id, 'dataframe_id': df_id} for df_id, in dataframes_for_add_ids])

        db.session.commit()

        flash('Кластер обновлён.')

    return render_template('core/cluster.html', cluster=clr, form=form)


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

        return redirect(url_for('core.cluster', pk=clr.id))

    return render_template('core/cluster_add.html', title='Добавить кластер', form=form)


@bp.route('/cluster/<pk>/delete/', methods=['GET', 'POST'])
def cluster_delete(pk):
    clr = Cluster.query.get_or_404(pk)

    form = EmptyForm()
    form.button.label.text = 'Удалить'

    if form.validate_on_submit():
        db.session.delete(clr)
        db.session.commit()
        flash(f'Кластер "{clr.name}" удалён.')

        return redirect(url_for('core.index'))

    return render_template('core/delete.html', title=f'Удалить кластер "{clr.name}" и всех его потомков?', form=form)
