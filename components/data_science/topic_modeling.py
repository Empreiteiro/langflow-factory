from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class TopicModeling(Component):
    display_name = "Topic Modeling"
    description = (
        "Extracts topics from a text column using Latent Dirichlet Allocation (LDA), "
        "Non-negative Matrix Factorization (NMF) on TF-IDF, or BERTopic."
    )
    icon = "mdi-format-list-bulleted-type"
    name = "TopicModeling"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="text_column",
            display_name="Text Column",
            required=True,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["lda", "nmf", "bertopic"],
            value="lda",
        ),
        IntInput(
            name="n_topics",
            display_name="Num Topics",
            value=10,
        ),
        IntInput(
            name="top_words",
            display_name="Top Words per Topic",
            value=10,
        ),
        IntInput(
            name="max_features",
            display_name="Max Vocabulary",
            value=1000,
        ),
    ]

    outputs = [
        Output(name="assignments", display_name="Topic Assignments", method="get_assignments"),
        Output(name="topics", display_name="Topic Keywords", method="get_topics"),
    ]

    def _vectorize(self, texts, use_tfidf: bool):
        from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
        cls = TfidfVectorizer if use_tfidf else CountVectorizer
        vectorizer = cls(max_features=int(self.max_features or 1000), stop_words="english")
        matrix = vectorizer.fit_transform(texts)
        return vectorizer, matrix

    def _top_words(self, feature_names, components, top_n):
        topics = []
        for idx, comp in enumerate(components):
            order = np.argsort(comp)[::-1][:top_n]
            words = [feature_names[i] for i in order]
            weights = [float(comp[i]) for i in order]
            topics.append({"topic": idx, "keywords": words, "weights": weights})
        return topics

    def _run(self):
        try:
            from sklearn.decomposition import LatentDirichletAllocation, NMF
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.text_column or self.text_column not in self.df.columns:
            raise ValueError(f"Text column '{self.text_column}' not found.")

        df = self.df.copy()
        texts = df[self.text_column].fillna("").astype(str).tolist()
        n_topics = int(self.n_topics or 10)
        top_n = int(self.top_words or 10)
        method = self.method or "lda"

        if method == "lda":
            vectorizer, matrix = self._vectorize(texts, use_tfidf=False)
            model = LatentDirichletAllocation(n_components=n_topics, random_state=42)
            doc_topics = model.fit_transform(matrix)
            components = model.components_
            feature_names = vectorizer.get_feature_names_out()
            topics = self._top_words(feature_names, components, top_n)
            assignments = np.argmax(doc_topics, axis=1)
        elif method == "nmf":
            vectorizer, matrix = self._vectorize(texts, use_tfidf=True)
            model = NMF(n_components=n_topics, random_state=42, init="nndsvd")
            doc_topics = model.fit_transform(matrix)
            components = model.components_
            feature_names = vectorizer.get_feature_names_out()
            topics = self._top_words(feature_names, components, top_n)
            assignments = np.argmax(doc_topics, axis=1)
        elif method == "bertopic":
            try:
                from bertopic import BERTopic
            except ImportError as exc:
                raise ImportError("bertopic is required. Install with: pip install bertopic") from exc
            model = BERTopic(nr_topics=n_topics, calculate_probabilities=False, verbose=False)
            assignments, _ = model.fit_transform(texts)
            topic_info = model.get_topic_info()
            topics = []
            for tid in topic_info["Topic"].tolist():
                words = model.get_topic(tid) or []
                topics.append({
                    "topic": int(tid),
                    "keywords": [w for w, _ in words[:top_n]],
                    "weights": [float(s) for _, s in words[:top_n]],
                })
        else:
            raise ValueError(f"Unsupported method: {method}")

        df["topic"] = assignments
        self._assignments = df
        self._topics = topics
        self._info = {"method": method, "n_topics": len(topics)}
        self.log(f"TopicModeling: {self._info}")

    def get_assignments(self) -> DataFrame:
        try:
            if not hasattr(self, "_assignments"):
                self._run()
            return DataFrame(self._assignments)
        except Exception as exc:
            self.log(f"TopicModeling failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_topics(self) -> Data:
        try:
            if not hasattr(self, "_topics"):
                self._run()
            return Data(data={"topics": self._topics, **self._info})
        except Exception as exc:
            return Data(data={"error": str(exc)})
