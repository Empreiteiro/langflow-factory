from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class TextEmbedder(Component):
    display_name = "Text Embedder"
    description = (
        "Encodes a text column into dense vector embeddings using sentence-transformers "
        "(default) or classic TF-IDF features."
    )
    icon = "mdi-vector-circle"
    name = "TextEmbedder"

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
            name="backend",
            display_name="Backend",
            options=["sentence_transformers", "tfidf"],
            value="sentence_transformers",
            real_time_refresh=True,
        ),
        StrInput(
            name="model_name",
            display_name="Model Name",
            info="sentence-transformers model id.",
            value="sentence-transformers/all-MiniLM-L6-v2",
        ),
        IntInput(
            name="batch_size",
            display_name="Batch Size",
            value=32,
        ),
        BoolInput(
            name="normalize",
            display_name="Normalize Embeddings",
            value=True,
        ),
        BoolInput(
            name="flatten",
            display_name="One Column per Dim",
            info="Expand the embedding into separate numeric columns.",
            value=False,
        ),
        IntInput(
            name="tfidf_max_features",
            display_name="TF-IDF Max Features",
            value=512,
        ),
    ]

    outputs = [
        Output(name="result", display_name="DataFrame with Embeddings", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _st(self, texts):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. Install with: pip install sentence-transformers"
            ) from exc
        model = SentenceTransformer(self.model_name)
        vectors = model.encode(
            texts,
            batch_size=int(self.batch_size or 32),
            normalize_embeddings=bool(self.normalize),
            show_progress_bar=False,
        )
        return vectors, getattr(model, "get_sentence_embedding_dimension", lambda: vectors.shape[1])()

    def _tfidf(self, texts):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as exc:
            raise ImportError("scikit-learn is required for TF-IDF.") from exc
        vectorizer = TfidfVectorizer(max_features=int(self.tfidf_max_features or 512))
        matrix = vectorizer.fit_transform(texts).toarray()
        return matrix, matrix.shape[1]

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.text_column or self.text_column not in self.df.columns:
            raise ValueError(f"Text column '{self.text_column}' not found.")

        df = self.df.copy()
        texts = df[self.text_column].fillna("").astype(str).tolist()

        if self.backend == "tfidf":
            vectors, dim = self._tfidf(texts)
        else:
            vectors, dim = self._st(texts)

        if self.flatten:
            emb_cols = [f"emb_{i}" for i in range(dim)]
            emb_df = pd.DataFrame(vectors, columns=emb_cols, index=df.index)
            result = pd.concat([df, emb_df], axis=1)
        else:
            result = df.copy()
            result["embedding"] = [list(map(float, row)) for row in vectors]

        self._result = result
        self._report = {
            "backend": self.backend,
            "model": self.model_name if self.backend == "sentence_transformers" else "tfidf",
            "rows": int(len(df)),
            "dim": int(dim),
            "flattened": bool(self.flatten),
        }
        self.log(f"TextEmbedder: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"TextEmbedder failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})
