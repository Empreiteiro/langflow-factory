from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    IntInput,
    MultilineInput,
    Output,
    StrInput,
)
from lfx.schema import Data
import json


class HyperparameterTuner(Component):
    display_name = "Hyperparameter Tuner"
    description = (
        "Runs Grid, Randomized or Optuna search over a user-supplied parameter grid, "
        "returning the best estimator and score."
    )
    icon = "mdi-tune"
    name = "HyperparameterTuner"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="target_column",
            display_name="Target Column",
            required=True,
        ),
        DropdownInput(
            name="task",
            display_name="Task",
            options=["classification", "regression"],
            value="classification",
        ),
        DropdownInput(
            name="model_type",
            display_name="Model",
            options=[
                "LogisticRegression",
                "RandomForestClassifier",
                "GradientBoostingClassifier",
                "SVC",
                "Ridge",
                "RandomForestRegressor",
                "GradientBoostingRegressor",
            ],
            value="RandomForestClassifier",
        ),
        MultilineInput(
            name="param_grid",
            display_name="Parameter Grid (JSON)",
            info='JSON dict of parameter lists, e.g. {"n_estimators": [100, 200], "max_depth": [5, 10]}.',
            required=True,
        ),
        DropdownInput(
            name="search",
            display_name="Search Type",
            options=["grid", "random", "optuna"],
            value="grid",
        ),
        IntInput(name="n_iter", display_name="n_iter (random/optuna)", value=20),
        IntInput(name="folds", display_name="CV Folds", value=5),
        DropdownInput(
            name="scoring",
            display_name="Scoring",
            options=[
                "accuracy", "f1_macro", "f1_weighted", "roc_auc",
                "r2", "neg_root_mean_squared_error",
            ],
            value="accuracy",
        ),
    ]

    outputs = [
        Output(name="best", display_name="Best Estimator", method="get_best"),
        Output(name="report", display_name="Search Report", method="get_report"),
    ]

    def _make_model(self, name):
        if name == "LogisticRegression":
            from sklearn.linear_model import LogisticRegression
            return LogisticRegression(max_iter=1000)
        if name == "RandomForestClassifier":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(random_state=42)
        if name == "GradientBoostingClassifier":
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(random_state=42)
        if name == "SVC":
            from sklearn.svm import SVC
            return SVC(probability=True)
        if name == "Ridge":
            from sklearn.linear_model import Ridge
            return Ridge()
        if name == "RandomForestRegressor":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(random_state=42)
        if name == "GradientBoostingRegressor":
            from sklearn.ensemble import GradientBoostingRegressor
            return GradientBoostingRegressor(random_state=42)
        raise ValueError(f"Unsupported model: {name}")

    def _parse_grid(self):
        if not self.param_grid:
            raise ValueError("param_grid is required.")
        try:
            grid = json.loads(self.param_grid)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in param_grid: {exc}") from exc
        if not isinstance(grid, dict) or not grid:
            raise ValueError("param_grid must be a non-empty JSON object.")
        return grid

    def _cv(self):
        from sklearn.model_selection import StratifiedKFold, KFold
        folds = int(self.folds or 5)
        if self.task == "classification":
            return StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        return KFold(n_splits=folds, shuffle=True, random_state=42)

    def _split_xy(self, df):
        X = df.drop(columns=[self.target_column]).select_dtypes(include="number")
        y = df[self.target_column]
        if X.empty:
            raise ValueError("No numeric features available.")
        return X, y

    def _run(self):
        try:
            from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")

        df = self.df.copy()
        X, y = self._split_xy(df)
        base = self._make_model(self.model_type)
        grid = self._parse_grid()
        cv = self._cv()
        search = self.search or "grid"

        if search == "grid":
            cvs = GridSearchCV(base, grid, cv=cv, scoring=self.scoring, n_jobs=-1)
            cvs.fit(X, y)
            best_estimator = cvs.best_estimator_
            best_params = cvs.best_params_
            best_score = float(cvs.best_score_)
        elif search == "random":
            cvs = RandomizedSearchCV(
                base, grid, n_iter=int(self.n_iter or 20), cv=cv,
                scoring=self.scoring, random_state=42, n_jobs=-1,
            )
            cvs.fit(X, y)
            best_estimator = cvs.best_estimator_
            best_params = cvs.best_params_
            best_score = float(cvs.best_score_)
        elif search == "optuna":
            try:
                import optuna
            except ImportError as exc:
                raise ImportError("optuna is required for 'optuna' search.") from exc

            def objective(trial):
                params = {}
                for key, values in grid.items():
                    if not isinstance(values, list) or not values:
                        raise ValueError(f"param_grid['{key}'] must be a non-empty list for optuna.")
                    params[key] = trial.suggest_categorical(key, values)
                model = self._make_model(self.model_type)
                model.set_params(**params)
                scores = cross_val_score(model, X, y, cv=cv, scoring=self.scoring, n_jobs=-1)
                return float(scores.mean())

            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=int(self.n_iter or 20), show_progress_bar=False)
            best_params = study.best_params
            best_score = float(study.best_value)
            best_estimator = self._make_model(self.model_type)
            best_estimator.set_params(**best_params)
            best_estimator.fit(X, y)
        else:
            raise ValueError(f"Unsupported search: {search}")

        self._best = best_estimator
        self._report = {
            "model_type": self.model_type,
            "search": search,
            "scoring": self.scoring,
            "folds": int(self.folds or 5),
            "best_params": best_params,
            "best_score": best_score,
        }
        self.log(f"HyperparameterTuner: {self._report}")

    def get_best(self) -> Data:
        try:
            if not hasattr(self, "_best"):
                self._run()
            return Data(data={"model": self._best, "report": self._report})
        except Exception as exc:
            self.log(f"HyperparameterTuner failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})
