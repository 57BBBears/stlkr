import pytest

from src.models import Check, Cluster, DataframeCluster, Resource, Url, UrlCheck


class TestModels:
    def test_create_models(self, session):
        # create a dataframe
        df = Resource(name="test")
        session.add(df)
        session.commit()

        query = Resource.query.one()
        assert query
        assert query.name == "test"

        # add an url to the dataframe
        url = Url(url="https://ya.ru", dataframe=df)
        session.add(url)
        session.commit()
        query = Url.query.filter_by(url="https://ya.ru", dataframe=df).one()
        assert query

        # adding wrong url must ends up with an error
        with pytest.raises(ValueError):
            url = Url(url="not url", dataframe=df)

        query = Url.query.filter_by(url="not url", dataframe=df).first()
        assert query is None

        # add a dataframe check
        check = Check(name="test check", dataframe=df)
        session.add(check)
        session.commit()

        query = Check.query.one()
        assert query
        assert query.name == "test check"

        # choose a dataframe active check
        df.active_check = check
        session.commit()
        assert df.active_check is check

        # dataframe active_check a one to one relationship test
        another_df = Resource(name="foo")
        session.add(another_df)
        session.commit()
        with pytest.raises(AttributeError):
            check.active_dataframe.append(another_df)

        # add a url check info
        raw_data = "<html><body><h1>Hello World!</h1></doby></html>"
        url_check = UrlCheck(check=check, url=url, status=404, raw_data=raw_data)
        session.add(url_check)
        session.commit()

        query = UrlCheck.query.one()
        assert query
        assert query.raw_data == raw_data
        assert query.check_time is not None

        # last_modified field test autoupdate
        assert query.last_modified is None
        url_check.status = 200
        session.commit()
        query = UrlCheck.query.one()
        assert query.last_modified is not None

        # Cluster
        cluster = Cluster(name="test cluster")
        session.add(cluster)
        session.commit()

        query = Cluster.query.one()

        assert query
        # slug autofill test
        assert query.slug == "test-cluster"

        # add dataframes to a cluster
        cluster.dataframes.append(df)
        cluster.dataframes.append(another_df)
        # count dataframes of a cluster
        query = (
            Resource.query.join(DataframeCluster)
            .filter_by(cluster_id=cluster.id)
            .count()
        )
        assert query == 2

        # set a parent cluster
        another_cluster = Cluster(name="foo cluster")
        another_cluster.parent = cluster
        session.add(another_cluster)
        session.commit()
        assert cluster.children == [another_cluster]

        # count clusters of a dataframe with two clusters
        df.clusters.append(another_cluster)
        query = (
            Cluster.query.join(DataframeCluster).filter_by(dataframe_id=df.id).count()
        )
        assert query == 2

    def test_delete_models(self, session):
        # Cluster
        cluster = Cluster(name="test cluster")
        session.add(cluster)
        session.commit()

        query = Cluster.query.count()
        assert query == 1

        # child cluster is deleted when parent cluster is deleted
        session.delete(cluster)
        session.commit()

        query = Cluster.query.count()
        assert query == 0
