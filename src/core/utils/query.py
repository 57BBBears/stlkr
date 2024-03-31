from sqlalchemy import and_, exists
from sqlalchemy.orm import Query

from src import db
from src.models import Check, DataframeProperty, Url, UrlCheck, UrlProperty


def get_unchecked_urls_stmt(check_id: int, limit: int = None):
    """Select urls that don't have parsed data."""
    df_id = (
        db.session.query(Check.dataframe_id).filter_by(id=check_id).scalar_subquery()
    )

    unchecked_urls_stmt = db.session.query(Url.id, Url.url).where(
        and_(
            Url.dataframe_id == df_id,
            ~exists().where(Url.id == UrlCheck.url_id, UrlCheck.check_id == check_id),
        )
    )

    if limit:
        unchecked_urls_stmt = unchecked_urls_stmt.limit(limit)

    return unchecked_urls_stmt


def get_checked_urls_stmt(
    check_id, only_new: bool = True, limit: int = 0, offset: int = 0
) -> Query:
    """Get UrlChecks with parsed raw_data to extract selectors from there."""
    parsed_urls = UrlCheck.query.filter(
        UrlCheck.check_id == check_id, UrlCheck.status == 200, UrlCheck.raw_data != ""
    )

    if only_new:
        parsed_urls = parsed_urls.where(
            ~exists().where(
                UrlCheck.check_id == UrlProperty.check_id,
                UrlCheck.url_id == UrlProperty.url_id,
            )
        )
        """
        parsed_urls = parsed_urls.outerjoin(UrlProperty,
                                            UrlCheck.check_id == UrlProperty.check_id
                                            ).filter(UrlProperty.data.is_(None))
        """

    if limit:
        parsed_urls = parsed_urls.limit(limit)

    if offset:
        parsed_urls = parsed_urls.offset(offset)

    return parsed_urls


def get_dataframe_selectors(df_id: int) -> dict[int, str]:
    """Return property selectors of the dataframe."""
    df_properties = DataframeProperty.query.filter_by(dataframe_id=df_id).all()
    return {prop.property_id: prop.selector for prop in df_properties}
