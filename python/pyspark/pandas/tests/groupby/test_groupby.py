#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest
import inspect

import numpy as np
import pandas as pd

from pyspark import pandas as ps
from pyspark.pandas.exceptions import PandasNotImplementedError, DataError
from pyspark.pandas.missing.groupby import (
    MissingPandasLikeDataFrameGroupBy,
    MissingPandasLikeSeriesGroupBy,
)
from pyspark.pandas.groupby import is_multi_agg_with_relabel, SeriesGroupBy
from pyspark.testing.pandasutils import PandasOnSparkTestCase, TestUtils


class GroupByTestsMixin:
    @property
    def pdf(self):
        return pd.DataFrame(
            {
                "A": [1, 2, 1, 2],
                "B": [3.1, 4.1, 4.1, 3.1],
                "C": ["a", "b", "b", "a"],
                "D": [True, False, False, True],
            }
        )

    @property
    def psdf(self):
        return ps.from_pandas(self.pdf)

    def test_groupby_simple(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 2, 6, 4, 4, 6, 4, 3, 7],
                "b": [4, 2, 7, 3, 3, 1, 1, 1, 2],
                "c": [4, 2, 7, 3, None, 1, 1, 1, 2],
                "d": list("abcdefght"),
                "e": [True, False, True, False, True, False, True, False, True],
            },
            index=[0, 1, 3, 5, 6, 8, 9, 9, 9],
        )
        psdf = ps.from_pandas(pdf)

        for as_index in [True, False]:
            if as_index:

                def sort(df):
                    return df.sort_index()

            else:

                def sort(df):
                    return df.sort_values("a").reset_index(drop=True)

            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index).sum()),
                sort(pdf.groupby("a", as_index=as_index).sum()),
            )
            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index).b.sum()),
                sort(pdf.groupby("a", as_index=as_index).b.sum()),
            )
            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index)["b"].sum()),
                sort(pdf.groupby("a", as_index=as_index)["b"].sum()),
            )
            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index)[["b", "c"]].sum()),
                sort(pdf.groupby("a", as_index=as_index)[["b", "c"]].sum()),
            )
            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index)[[]].sum()),
                sort(pdf.groupby("a", as_index=as_index)[[]].sum()),
            )
            self.assert_eq(
                sort(psdf.groupby("a", as_index=as_index)["c"].sum()),
                sort(pdf.groupby("a", as_index=as_index)["c"].sum()),
            )

        self.assert_eq(
            psdf.groupby("a").a.sum().sort_index(), pdf.groupby("a").a.sum().sort_index()
        )
        self.assert_eq(
            psdf.groupby("a")["a"].sum().sort_index(), pdf.groupby("a")["a"].sum().sort_index()
        )
        self.assert_eq(
            psdf.groupby("a")[["a"]].sum().sort_index(), pdf.groupby("a")[["a"]].sum().sort_index()
        )
        self.assert_eq(
            psdf.groupby("a")[["a", "c"]].sum().sort_index(),
            pdf.groupby("a")[["a", "c"]].sum().sort_index(),
        )

        self.assert_eq(
            psdf.a.groupby(psdf.b).sum().sort_index(), pdf.a.groupby(pdf.b).sum().sort_index()
        )

        for axis in [0, "index"]:
            self.assert_eq(
                psdf.groupby("a", axis=axis).a.sum().sort_index(),
                pdf.groupby("a", axis=axis).a.sum().sort_index(),
            )
            self.assert_eq(
                psdf.groupby("a", axis=axis)["a"].sum().sort_index(),
                pdf.groupby("a", axis=axis)["a"].sum().sort_index(),
            )
            self.assert_eq(
                psdf.groupby("a", axis=axis)[["a"]].sum().sort_index(),
                pdf.groupby("a", axis=axis)[["a"]].sum().sort_index(),
            )
            self.assert_eq(
                psdf.groupby("a", axis=axis)[["a", "c"]].sum().sort_index(),
                pdf.groupby("a", axis=axis)[["a", "c"]].sum().sort_index(),
            )

            self.assert_eq(
                psdf.a.groupby(psdf.b, axis=axis).sum().sort_index(),
                pdf.a.groupby(pdf.b, axis=axis).sum().sort_index(),
            )

        self.assertRaises(ValueError, lambda: psdf.groupby("a", as_index=False).a)
        self.assertRaises(ValueError, lambda: psdf.groupby("a", as_index=False)["a"])
        self.assertRaises(ValueError, lambda: psdf.groupby("a", as_index=False)[["a"]])
        self.assertRaises(ValueError, lambda: psdf.groupby("a", as_index=False)[["a", "c"]])
        self.assertRaises(KeyError, lambda: psdf.groupby("z", as_index=False)[["a", "c"]])
        self.assertRaises(KeyError, lambda: psdf.groupby(["z"], as_index=False)[["a", "c"]])

        self.assertRaises(TypeError, lambda: psdf.a.groupby(psdf.b, as_index=False))

        self.assertRaises(NotImplementedError, lambda: psdf.groupby("a", axis=1))
        self.assertRaises(NotImplementedError, lambda: psdf.groupby("a", axis="columns"))
        self.assertRaises(ValueError, lambda: psdf.groupby("a", "b"))
        self.assertRaises(TypeError, lambda: psdf.a.groupby(psdf.a, psdf.b))

        # we can't use column name/names as a parameter `by` for `SeriesGroupBy`.
        self.assertRaises(KeyError, lambda: psdf.a.groupby(by="a"))
        self.assertRaises(KeyError, lambda: psdf.a.groupby(by=["a", "b"]))
        self.assertRaises(KeyError, lambda: psdf.a.groupby(by=("a", "b")))
        self.assertRaises(KeyError, lambda: psdf.a.groupby(by=[("a", "b")]))

        # we can't use DataFrame as a parameter `by` for `DataFrameGroupBy`/`SeriesGroupBy`.
        self.assertRaises(ValueError, lambda: psdf.groupby(psdf))
        self.assertRaises(ValueError, lambda: psdf.a.groupby(psdf))
        self.assertRaises(ValueError, lambda: psdf.a.groupby((psdf,)))

        with self.assertRaisesRegex(ValueError, "Grouper for 'list' not 1-dimensional"):
            psdf.groupby(by=[["a", "b"]])

        # non-string names
        pdf = pd.DataFrame(
            {
                10: [1, 2, 6, 4, 4, 6, 4, 3, 7],
                20: [4, 2, 7, 3, 3, 1, 1, 1, 2],
                30: [4, 2, 7, 3, None, 1, 1, 1, 2],
                40: list("abcdefght"),
            },
            index=[0, 1, 3, 5, 6, 8, 9, 9, 9],
        )
        psdf = ps.from_pandas(pdf)

        for as_index in [True, False]:
            if as_index:

                def sort(df):
                    return df.sort_index()

            else:

                def sort(df):
                    return df.sort_values(10).reset_index(drop=True)

            self.assert_eq(
                sort(psdf.groupby(10, as_index=as_index).sum()),
                sort(pdf.groupby(10, as_index=as_index).sum()),
            )
            self.assert_eq(
                sort(psdf.groupby(10, as_index=as_index)[20].sum()),
                sort(pdf.groupby(10, as_index=as_index)[20].sum()),
            )
            self.assert_eq(
                sort(psdf.groupby(10, as_index=as_index)[[20, 30]].sum()),
                sort(pdf.groupby(10, as_index=as_index)[[20, 30]].sum()),
            )

    def test_nsmallest(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 1, 1, 2, 2, 2, 3, 3, 3] * 3,
                "b": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
                "c": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
                "d": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
            },
            index=np.random.rand(9 * 3),
        )
        psdf = ps.from_pandas(pdf)

        self.assert_eq(
            psdf.groupby(["a"])["b"].nsmallest(1).sort_values(),
            pdf.groupby(["a"])["b"].nsmallest(1).sort_values(),
        )
        self.assert_eq(
            psdf.groupby(["a"])["b"].nsmallest(2).sort_index(),
            pdf.groupby(["a"])["b"].nsmallest(2).sort_index(),
        )
        self.assert_eq(
            (psdf.b * 10).groupby(psdf.a).nsmallest(2).sort_index(),
            (pdf.b * 10).groupby(pdf.a).nsmallest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.rename().groupby(psdf.a).nsmallest(2).sort_index(),
            pdf.b.rename().groupby(pdf.a).nsmallest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.groupby(psdf.a.rename()).nsmallest(2).sort_index(),
            pdf.b.groupby(pdf.a.rename()).nsmallest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.rename().groupby(psdf.a.rename()).nsmallest(2).sort_index(),
            pdf.b.rename().groupby(pdf.a.rename()).nsmallest(2).sort_index(),
        )
        with self.assertRaisesRegex(ValueError, "nsmallest do not support multi-index now"):
            psdf.set_index(["a", "b"]).groupby(["c"])["d"].nsmallest(1)

    def test_nlargest(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 1, 1, 2, 2, 2, 3, 3, 3] * 3,
                "b": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
                "c": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
                "d": [1, 2, 2, 2, 3, 3, 3, 4, 4] * 3,
            },
            index=np.random.rand(9 * 3),
        )
        psdf = ps.from_pandas(pdf)

        self.assert_eq(
            psdf.groupby(["a"])["b"].nlargest(1).sort_values(),
            pdf.groupby(["a"])["b"].nlargest(1).sort_values(),
        )
        self.assert_eq(
            psdf.groupby(["a"])["b"].nlargest(2).sort_index(),
            pdf.groupby(["a"])["b"].nlargest(2).sort_index(),
        )
        self.assert_eq(
            (psdf.b * 10).groupby(psdf.a).nlargest(2).sort_index(),
            (pdf.b * 10).groupby(pdf.a).nlargest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.rename().groupby(psdf.a).nlargest(2).sort_index(),
            pdf.b.rename().groupby(pdf.a).nlargest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.groupby(psdf.a.rename()).nlargest(2).sort_index(),
            pdf.b.groupby(pdf.a.rename()).nlargest(2).sort_index(),
        )
        self.assert_eq(
            psdf.b.rename().groupby(psdf.a.rename()).nlargest(2).sort_index(),
            pdf.b.rename().groupby(pdf.a.rename()).nlargest(2).sort_index(),
        )
        with self.assertRaisesRegex(ValueError, "nlargest do not support multi-index now"):
            psdf.set_index(["a", "b"]).groupby(["c"])["d"].nlargest(1)

    def test_shift(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 1, 2, 2, 3, 3] * 3,
                "b": [1, 1, 2, 2, 3, 4] * 3,
                "c": [1, 4, 9, 16, 25, 36] * 3,
            },
            index=np.random.rand(6 * 3),
        )
        psdf = ps.from_pandas(pdf)

        self.assert_eq(
            psdf.groupby("a").shift().sort_index(), pdf.groupby("a").shift().sort_index()
        )
        # TODO: seems like a pandas' bug when fill_value is not None?
        # self.assert_eq(psdf.groupby(['a', 'b']).shift(periods=-1, fill_value=0).sort_index(),
        #                pdf.groupby(['a', 'b']).shift(periods=-1, fill_value=0).sort_index())
        self.assert_eq(
            psdf.groupby(["b"])["a"].shift().sort_index(),
            pdf.groupby(["b"])["a"].shift().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["a", "b"])["c"].shift().sort_index(),
            pdf.groupby(["a", "b"])["c"].shift().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5).shift().sort_index(),
            pdf.groupby(pdf.b // 5).shift().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5)["a"].shift().sort_index(),
            pdf.groupby(pdf.b // 5)["a"].shift().sort_index(),
        )
        self.assert_eq(
            psdf.a.rename().groupby(psdf.b).shift().sort_index(),
            pdf.a.rename().groupby(pdf.b).shift().sort_index(),
        )
        self.assert_eq(
            psdf.a.groupby(psdf.b.rename()).shift().sort_index(),
            pdf.a.groupby(pdf.b.rename()).shift().sort_index(),
        )
        self.assert_eq(
            psdf.a.rename().groupby(psdf.b.rename()).shift().sort_index(),
            pdf.a.rename().groupby(pdf.b.rename()).shift().sort_index(),
        )

        self.assert_eq(psdf.groupby("a").shift().sum(), pdf.groupby("a").shift().sum().astype(int))
        self.assert_eq(
            psdf.a.rename().groupby(psdf.b).shift().sum(),
            pdf.a.rename().groupby(pdf.b).shift().sum(),
        )

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("x", "a"), ("x", "b"), ("y", "c")])
        pdf.columns = columns
        psdf.columns = columns

        self.assert_eq(
            psdf.groupby(("x", "a")).shift().sort_index(),
            pdf.groupby(("x", "a")).shift().sort_index(),
        )
        # TODO: seems like a pandas' bug when fill_value is not None?
        # self.assert_eq(psdf.groupby([('x', 'a'), ('x', 'b')]).shift(periods=-1,
        #                                                            fill_value=0).sort_index(),
        #                pdf.groupby([('x', 'a'), ('x', 'b')]).shift(periods=-1,
        #                                                            fill_value=0).sort_index())

    def test_missing(self):
        psdf = ps.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9]})

        # DataFrameGroupBy functions
        missing_functions = inspect.getmembers(
            MissingPandasLikeDataFrameGroupBy, inspect.isfunction
        )
        unsupported_functions = [
            name for (name, type_) in missing_functions if type_.__name__ == "unsupported_function"
        ]
        for name in unsupported_functions:
            with self.assertRaisesRegex(
                PandasNotImplementedError,
                "method.*GroupBy.*{}.*not implemented( yet\\.|\\. .+)".format(name),
            ):
                getattr(psdf.groupby("a"), name)()

        deprecated_functions = [
            name for (name, type_) in missing_functions if type_.__name__ == "deprecated_function"
        ]
        for name in deprecated_functions:
            with self.assertRaisesRegex(
                PandasNotImplementedError, "method.*GroupBy.*{}.*is deprecated".format(name)
            ):
                getattr(psdf.groupby("a"), name)()

        # SeriesGroupBy functions
        missing_functions = inspect.getmembers(MissingPandasLikeSeriesGroupBy, inspect.isfunction)
        unsupported_functions = [
            name for (name, type_) in missing_functions if type_.__name__ == "unsupported_function"
        ]
        for name in unsupported_functions:
            with self.assertRaisesRegex(
                PandasNotImplementedError,
                "method.*GroupBy.*{}.*not implemented( yet\\.|\\. .+)".format(name),
            ):
                getattr(psdf.a.groupby(psdf.a), name)()

        deprecated_functions = [
            name for (name, type_) in missing_functions if type_.__name__ == "deprecated_function"
        ]
        for name in deprecated_functions:
            with self.assertRaisesRegex(
                PandasNotImplementedError, "method.*GroupBy.*{}.*is deprecated".format(name)
            ):
                getattr(psdf.a.groupby(psdf.a), name)()

        # DataFrameGroupBy properties
        missing_properties = inspect.getmembers(
            MissingPandasLikeDataFrameGroupBy, lambda o: isinstance(o, property)
        )
        unsupported_properties = [
            name
            for (name, type_) in missing_properties
            if type_.fget.__name__ == "unsupported_property"
        ]
        for name in unsupported_properties:
            with self.assertRaisesRegex(
                PandasNotImplementedError,
                "property.*GroupBy.*{}.*not implemented( yet\\.|\\. .+)".format(name),
            ):
                getattr(psdf.groupby("a"), name)
        deprecated_properties = [
            name
            for (name, type_) in missing_properties
            if type_.fget.__name__ == "deprecated_property"
        ]
        for name in deprecated_properties:
            with self.assertRaisesRegex(
                PandasNotImplementedError, "property.*GroupBy.*{}.*is deprecated".format(name)
            ):
                getattr(psdf.groupby("a"), name)

        # SeriesGroupBy properties
        missing_properties = inspect.getmembers(
            MissingPandasLikeSeriesGroupBy, lambda o: isinstance(o, property)
        )
        unsupported_properties = [
            name
            for (name, type_) in missing_properties
            if type_.fget.__name__ == "unsupported_property"
        ]
        for name in unsupported_properties:
            with self.assertRaisesRegex(
                PandasNotImplementedError,
                "property.*GroupBy.*{}.*not implemented( yet\\.|\\. .+)".format(name),
            ):
                getattr(psdf.a.groupby(psdf.a), name)
        deprecated_properties = [
            name
            for (name, type_) in missing_properties
            if type_.fget.__name__ == "deprecated_property"
        ]
        for name in deprecated_properties:
            with self.assertRaisesRegex(
                PandasNotImplementedError, "property.*GroupBy.*{}.*is deprecated".format(name)
            ):
                getattr(psdf.a.groupby(psdf.a), name)

    @staticmethod
    def test_is_multi_agg_with_relabel():

        assert is_multi_agg_with_relabel(a="max") is False
        assert is_multi_agg_with_relabel(a_min=("a", "max"), a_max=("a", "min")) is True

    def test_get_group(self):
        pdf = pd.DataFrame(
            [
                ("falcon", "bird", 389.0),
                ("parrot", "bird", 24.0),
                ("lion", "mammal", 80.5),
                ("monkey", "mammal", np.nan),
            ],
            columns=["name", "class", "max_speed"],
            index=[0, 2, 3, 1],
        )
        pdf.columns.name = "Koalas"
        psdf = ps.from_pandas(pdf)

        self.assert_eq(
            psdf.groupby("class").get_group("bird"),
            pdf.groupby("class").get_group("bird"),
        )
        self.assert_eq(
            psdf.groupby("class")["name"].get_group("mammal"),
            pdf.groupby("class")["name"].get_group("mammal"),
        )
        self.assert_eq(
            psdf.groupby("class")[["name"]].get_group("mammal"),
            pdf.groupby("class")[["name"]].get_group("mammal"),
        )
        self.assert_eq(
            psdf.groupby(["class", "name"]).get_group(("mammal", "lion")),
            pdf.groupby(["class", "name"]).get_group(("mammal", "lion")),
        )
        self.assert_eq(
            psdf.groupby(["class", "name"])["max_speed"].get_group(("mammal", "lion")),
            pdf.groupby(["class", "name"])["max_speed"].get_group(("mammal", "lion")),
        )
        self.assert_eq(
            psdf.groupby(["class", "name"])[["max_speed"]].get_group(("mammal", "lion")),
            pdf.groupby(["class", "name"])[["max_speed"]].get_group(("mammal", "lion")),
        )
        self.assert_eq(
            (psdf.max_speed + 1).groupby(psdf["class"]).get_group("mammal"),
            (pdf.max_speed + 1).groupby(pdf["class"]).get_group("mammal"),
        )
        self.assert_eq(
            psdf.groupby("max_speed").get_group(80.5),
            pdf.groupby("max_speed").get_group(80.5),
        )

        self.assertRaises(KeyError, lambda: psdf.groupby("class").get_group("fish"))
        self.assertRaises(TypeError, lambda: psdf.groupby("class").get_group(["bird", "mammal"]))
        self.assertRaises(KeyError, lambda: psdf.groupby("class")["name"].get_group("fish"))
        self.assertRaises(
            TypeError, lambda: psdf.groupby("class")["name"].get_group(["bird", "mammal"])
        )
        self.assertRaises(
            KeyError, lambda: psdf.groupby(["class", "name"]).get_group(("lion", "mammal"))
        )
        self.assertRaises(ValueError, lambda: psdf.groupby(["class", "name"]).get_group(("lion",)))
        self.assertRaises(
            ValueError, lambda: psdf.groupby(["class", "name"]).get_group(("mammal",))
        )
        self.assertRaises(ValueError, lambda: psdf.groupby(["class", "name"]).get_group("mammal"))

        # MultiIndex columns
        pdf.columns = pd.MultiIndex.from_tuples([("A", "name"), ("B", "class"), ("C", "max_speed")])
        pdf.columns.names = ["Hello", "Koalas"]
        psdf = ps.from_pandas(pdf)
        self.assert_eq(
            psdf.groupby(("B", "class")).get_group("bird"),
            pdf.groupby(("B", "class")).get_group("bird"),
        )
        self.assert_eq(
            psdf.groupby(("B", "class"))[[("A", "name")]].get_group("mammal"),
            pdf.groupby(("B", "class"))[[("A", "name")]].get_group("mammal"),
        )
        self.assert_eq(
            psdf.groupby([("B", "class"), ("A", "name")]).get_group(("mammal", "lion")),
            pdf.groupby([("B", "class"), ("A", "name")]).get_group(("mammal", "lion")),
        )
        self.assert_eq(
            psdf.groupby([("B", "class"), ("A", "name")])[[("C", "max_speed")]].get_group(
                ("mammal", "lion")
            ),
            pdf.groupby([("B", "class"), ("A", "name")])[[("C", "max_speed")]].get_group(
                ("mammal", "lion")
            ),
        )
        self.assert_eq(
            (psdf[("C", "max_speed")] + 1).groupby(psdf[("B", "class")]).get_group("mammal"),
            (pdf[("C", "max_speed")] + 1).groupby(pdf[("B", "class")]).get_group("mammal"),
        )
        self.assert_eq(
            psdf.groupby(("C", "max_speed")).get_group(80.5),
            pdf.groupby(("C", "max_speed")).get_group(80.5),
        )

        self.assertRaises(KeyError, lambda: psdf.groupby(("B", "class")).get_group("fish"))
        self.assertRaises(
            TypeError, lambda: psdf.groupby(("B", "class")).get_group(["bird", "mammal"])
        )
        self.assertRaises(
            KeyError, lambda: psdf.groupby(("B", "class"))[("A", "name")].get_group("fish")
        )
        self.assertRaises(
            KeyError,
            lambda: psdf.groupby([("B", "class"), ("A", "name")]).get_group(("lion", "mammal")),
        )
        self.assertRaises(
            ValueError,
            lambda: psdf.groupby([("B", "class"), ("A", "name")]).get_group(("lion",)),
        )
        self.assertRaises(
            ValueError, lambda: psdf.groupby([("B", "class"), ("A", "name")]).get_group(("mammal",))
        )
        self.assertRaises(
            ValueError, lambda: psdf.groupby([("B", "class"), ("A", "name")]).get_group("mammal")
        )

    def test_getitem(self):
        psdf = ps.DataFrame(
            {
                "a": [1, 1, 1, 1, 2, 2, 2, 3, 3, 3] * 3,
                "b": [2, 3, 1, 4, 6, 9, 8, 10, 7, 5] * 3,
                "c": [3, 5, 2, 5, 1, 2, 6, 4, 3, 6] * 3,
            },
            index=np.random.rand(10 * 3),
        )

        self.assertTrue(isinstance(psdf.groupby("a")["b"], SeriesGroupBy))

    def test_all_any(self):
        pdf = pd.DataFrame(
            {
                "A": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
                "B": [True, True, True, False, False, False, None, True, None, False],
            }
        )
        psdf = ps.from_pandas(pdf)

        for as_index in [True, False]:
            if as_index:

                def sort(df):
                    return df.sort_index()

            else:

                def sort(df):
                    return df.sort_values("A").reset_index(drop=True)

            self.assert_eq(
                sort(psdf.groupby("A", as_index=as_index).all()),
                sort(pdf.groupby("A", as_index=as_index).all()),
            )
            self.assert_eq(
                sort(psdf.groupby("A", as_index=as_index).any()),
                sort(pdf.groupby("A", as_index=as_index).any()),
            )

            self.assert_eq(
                sort(psdf.groupby("A", as_index=as_index).all()).B,
                sort(pdf.groupby("A", as_index=as_index).all()).B,
            )
            self.assert_eq(
                sort(psdf.groupby("A", as_index=as_index).any()).B,
                sort(pdf.groupby("A", as_index=as_index).any()).B,
            )

        self.assert_eq(
            psdf.B.groupby(psdf.A).all().sort_index(), pdf.B.groupby(pdf.A).all().sort_index()
        )
        self.assert_eq(
            psdf.B.groupby(psdf.A).any().sort_index(), pdf.B.groupby(pdf.A).any().sort_index()
        )

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("X", "A"), ("Y", "B")])
        pdf.columns = columns
        psdf.columns = columns

        for as_index in [True, False]:
            if as_index:

                def sort(df):
                    return df.sort_index()

            else:

                def sort(df):
                    return df.sort_values(("X", "A")).reset_index(drop=True)

            self.assert_eq(
                sort(psdf.groupby(("X", "A"), as_index=as_index).all()),
                sort(pdf.groupby(("X", "A"), as_index=as_index).all()),
            )
            self.assert_eq(
                sort(psdf.groupby(("X", "A"), as_index=as_index).any()),
                sort(pdf.groupby(("X", "A"), as_index=as_index).any()),
            )

        # Test skipna
        pdf = pd.DataFrame({"A": [True, True], "B": [1, np.nan], "C": [True, None]})
        pdf.name = "x"
        psdf = ps.from_pandas(pdf)
        self.assert_eq(
            psdf.groupby("A").all(skipna=False).sort_index(),
            pdf.groupby("A").all(skipna=False).sort_index(),
        )
        self.assert_eq(
            psdf.groupby("A").all(skipna=True).sort_index(),
            pdf.groupby("A").all(skipna=True).sort_index(),
        )

    def test_raises(self):
        psdf = ps.DataFrame(
            {"a": [1, 2, 6, 4, 4, 6, 4, 3, 7], "b": [4, 2, 7, 3, 3, 1, 1, 1, 2]},
            index=[0, 1, 3, 5, 6, 8, 9, 9, 9],
        )
        # test raises with incorrect key
        self.assertRaises(ValueError, lambda: psdf.groupby([]))
        self.assertRaises(KeyError, lambda: psdf.groupby("x"))
        self.assertRaises(KeyError, lambda: psdf.groupby(["a", "x"]))
        self.assertRaises(KeyError, lambda: psdf.groupby("a")["x"])
        self.assertRaises(KeyError, lambda: psdf.groupby("a")["b", "x"])
        self.assertRaises(KeyError, lambda: psdf.groupby("a")[["b", "x"]])

    def test_nunique(self):
        pdf = pd.DataFrame(
            {"a": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0], "b": [2, 2, 2, 3, 3, 4, 4, 5, 5, 5]}
        )
        psdf = ps.from_pandas(pdf)
        self.assert_eq(
            psdf.groupby("a").agg({"b": "nunique"}).sort_index(),
            pdf.groupby("a").agg({"b": "nunique"}).sort_index(),
        )
        self.assert_eq(
            psdf.groupby("a").nunique().sort_index(), pdf.groupby("a").nunique().sort_index()
        )
        self.assert_eq(
            psdf.groupby("a").nunique(dropna=False).sort_index(),
            pdf.groupby("a").nunique(dropna=False).sort_index(),
        )
        self.assert_eq(
            psdf.groupby("a")["b"].nunique().sort_index(),
            pdf.groupby("a")["b"].nunique().sort_index(),
        )
        self.assert_eq(
            psdf.groupby("a")["b"].nunique(dropna=False).sort_index(),
            pdf.groupby("a")["b"].nunique(dropna=False).sort_index(),
        )

        nunique_psdf = psdf.groupby("a", as_index=False).agg({"b": "nunique"})
        nunique_pdf = pdf.groupby("a", as_index=False).agg({"b": "nunique"})
        self.assert_eq(
            nunique_psdf.sort_values(["a", "b"]).reset_index(drop=True),
            nunique_pdf.sort_values(["a", "b"]).reset_index(drop=True),
        )

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("x", "a"), ("y", "b")])
        pdf.columns = columns
        psdf.columns = columns

        self.assert_eq(
            psdf.groupby(("x", "a")).nunique().sort_index(),
            pdf.groupby(("x", "a")).nunique().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(("x", "a")).nunique(dropna=False).sort_index(),
            pdf.groupby(("x", "a")).nunique(dropna=False).sort_index(),
        )

    def test_unique(self):
        for pdf in [
            pd.DataFrame(
                {"a": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0], "b": [2, 2, 2, 3, 3, 4, 4, 5, 5, 5]}
            ),
            pd.DataFrame(
                {
                    "a": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                    "b": ["w", "w", "w", "x", "x", "y", "y", "z", "z", "z"],
                }
            ),
        ]:
            with self.subTest(pdf=pdf):
                psdf = ps.from_pandas(pdf)

                actual = psdf.groupby("a")["b"].unique().sort_index()._to_pandas()
                expect = pdf.groupby("a")["b"].unique().sort_index()
                self.assert_eq(len(actual), len(expect))
                for act, exp in zip(actual, expect):
                    self.assertTrue(sorted(act) == sorted(exp))

    def test_value_counts(self):
        pdf = pd.DataFrame(
            {"A": [np.nan, 2, 2, 3, 3, 3], "B": [1, 1, 2, 3, 3, np.nan]}, columns=["A", "B"]
        )
        psdf = ps.from_pandas(pdf)
        self.assert_eq(
            psdf.groupby("A")["B"].value_counts().sort_index(),
            pdf.groupby("A")["B"].value_counts().sort_index(),
        )
        self.assert_eq(
            psdf.groupby("A")["B"].value_counts(dropna=False).sort_index(),
            pdf.groupby("A")["B"].value_counts(dropna=False).sort_index(),
            almost=True,
        )
        self.assert_eq(
            psdf.groupby("A", dropna=False)["B"].value_counts(dropna=False).sort_index(),
            pdf.groupby("A", dropna=False)["B"].value_counts(dropna=False).sort_index(),
            # Returns are the same considering values and types,
            # disable check_exact to pass the assert_eq
            check_exact=False,
        )
        self.assert_eq(
            psdf.groupby("A")["B"].value_counts(sort=True, ascending=False).sort_index(),
            pdf.groupby("A")["B"].value_counts(sort=True, ascending=False).sort_index(),
        )
        self.assert_eq(
            psdf.groupby("A")["B"]
            .value_counts(sort=True, ascending=False, dropna=False)
            .sort_index(),
            pdf.groupby("A")["B"]
            .value_counts(sort=True, ascending=False, dropna=False)
            .sort_index(),
            almost=True,
        )
        self.assert_eq(
            psdf.groupby("A")["B"]
            .value_counts(sort=True, ascending=True, dropna=False)
            .sort_index(),
            pdf.groupby("A")["B"]
            .value_counts(sort=True, ascending=True, dropna=False)
            .sort_index(),
            almost=True,
        )
        self.assert_eq(
            psdf.B.rename().groupby(psdf.A).value_counts().sort_index(),
            pdf.B.rename().groupby(pdf.A).value_counts().sort_index(),
        )
        self.assert_eq(
            psdf.B.rename().groupby(psdf.A, dropna=False).value_counts().sort_index(),
            pdf.B.rename().groupby(pdf.A, dropna=False).value_counts().sort_index(),
            # Returns are the same considering values and types,
            # disable check_exact to pass the assert_eq
            check_exact=False,
        )
        self.assert_eq(
            psdf.B.groupby(psdf.A.rename()).value_counts().sort_index(),
            pdf.B.groupby(pdf.A.rename()).value_counts().sort_index(),
        )
        self.assert_eq(
            psdf.B.rename().groupby(psdf.A.rename()).value_counts().sort_index(),
            pdf.B.rename().groupby(pdf.A.rename()).value_counts().sort_index(),
        )

    def test_size(self):
        pdf = pd.DataFrame({"A": [1, 2, 2, 3, 3, 3], "B": [1, 1, 2, 3, 3, 3]})
        psdf = ps.from_pandas(pdf)
        self.assert_eq(psdf.groupby("A").size().sort_index(), pdf.groupby("A").size().sort_index())
        self.assert_eq(
            psdf.groupby("A")["B"].size().sort_index(), pdf.groupby("A")["B"].size().sort_index()
        )
        self.assert_eq(
            psdf.groupby("A")[["B"]].size().sort_index(),
            pdf.groupby("A")[["B"]].size().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["A", "B"]).size().sort_index(),
            pdf.groupby(["A", "B"]).size().sort_index(),
        )

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("X", "A"), ("Y", "B")])
        pdf.columns = columns
        psdf.columns = columns

        self.assert_eq(
            psdf.groupby(("X", "A")).size().sort_index(),
            pdf.groupby(("X", "A")).size().sort_index(),
        )
        self.assert_eq(
            psdf.groupby([("X", "A"), ("Y", "B")]).size().sort_index(),
            pdf.groupby([("X", "A"), ("Y", "B")]).size().sort_index(),
        )

    def test_diff(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5, 6] * 3,
                "b": [1, 1, 2, 3, 5, 8] * 3,
                "c": [1, 4, 9, 16, 25, 36] * 3,
            }
        )
        psdf = ps.from_pandas(pdf)

        self.assert_eq(psdf.groupby("b").diff().sort_index(), pdf.groupby("b").diff().sort_index())
        self.assert_eq(
            psdf.groupby(["a", "b"]).diff().sort_index(),
            pdf.groupby(["a", "b"]).diff().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["b"])["a"].diff().sort_index(),
            pdf.groupby(["b"])["a"].diff().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["b"])[["a", "b"]].diff().sort_index(),
            pdf.groupby(["b"])[["a", "b"]].diff().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5).diff().sort_index(),
            pdf.groupby(pdf.b // 5).diff().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5)["a"].diff().sort_index(),
            pdf.groupby(pdf.b // 5)["a"].diff().sort_index(),
        )

        self.assert_eq(psdf.groupby("b").diff().sum(), pdf.groupby("b").diff().sum().astype(int))
        self.assert_eq(psdf.groupby(["b"])["a"].diff().sum(), pdf.groupby(["b"])["a"].diff().sum())

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("x", "a"), ("x", "b"), ("y", "c")])
        pdf.columns = columns
        psdf.columns = columns

        self.assert_eq(
            psdf.groupby(("x", "b")).diff().sort_index(),
            pdf.groupby(("x", "b")).diff().sort_index(),
        )
        self.assert_eq(
            psdf.groupby([("x", "a"), ("x", "b")]).diff().sort_index(),
            pdf.groupby([("x", "a"), ("x", "b")]).diff().sort_index(),
        )

    def test_rank(self):
        pdf = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5, 6] * 3,
                "b": [1, 1, 2, 3, 5, 8] * 3,
                "c": [1, 4, 9, 16, 25, 36] * 3,
            },
            index=np.random.rand(6 * 3),
        )
        psdf = ps.from_pandas(pdf)

        self.assert_eq(psdf.groupby("b").rank().sort_index(), pdf.groupby("b").rank().sort_index())
        self.assert_eq(
            psdf.groupby(["a", "b"]).rank().sort_index(),
            pdf.groupby(["a", "b"]).rank().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["b"])["a"].rank().sort_index(),
            pdf.groupby(["b"])["a"].rank().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(["b"])[["a", "c"]].rank().sort_index(),
            pdf.groupby(["b"])[["a", "c"]].rank().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5).rank().sort_index(),
            pdf.groupby(pdf.b // 5).rank().sort_index(),
        )
        self.assert_eq(
            psdf.groupby(psdf.b // 5)["a"].rank().sort_index(),
            pdf.groupby(pdf.b // 5)["a"].rank().sort_index(),
        )

        self.assert_eq(psdf.groupby("b").rank().sum(), pdf.groupby("b").rank().sum())
        self.assert_eq(psdf.groupby(["b"])["a"].rank().sum(), pdf.groupby(["b"])["a"].rank().sum())

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("x", "a"), ("x", "b"), ("y", "c")])
        pdf.columns = columns
        psdf.columns = columns

        self.assert_eq(
            psdf.groupby(("x", "b")).rank().sort_index(),
            pdf.groupby(("x", "b")).rank().sort_index(),
        )
        self.assert_eq(
            psdf.groupby([("x", "a"), ("x", "b")]).rank().sort_index(),
            pdf.groupby([("x", "a"), ("x", "b")]).rank().sort_index(),
        )


class GroupByTests(GroupByTestsMixin, PandasOnSparkTestCase, TestUtils):
    pass


if __name__ == "__main__":
    from pyspark.pandas.tests.groupby.test_groupby import *  # noqa: F401

    try:
        import xmlrunner

        testRunner = xmlrunner.XMLTestRunner(output="target/test-reports", verbosity=2)
    except ImportError:
        testRunner = None
    unittest.main(testRunner=testRunner, verbosity=2)
