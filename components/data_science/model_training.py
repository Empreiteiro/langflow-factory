from lfx.custom import Component
from lfx.io import DataFrameInput, DropdownInput, FloatInput, StrInput, Output
from lfx.schema import DataFrame, Data
import pandas as pd

class TrainTestSplitModel(Component):
    display_name = "Train/Test Split & Model Trainer"
    description = "Splits a DataFrame into training and test sets and trains a selected ML model. Supports 11 different algorithms including ensemble, linear, tree-based, and boosting models."
    icon = "mdi-robot"
    name = "TrainTestSplitModel"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="Input DataFrame with features and target.",
            required=True,
        ),
        StrInput(
            name="target_column",
            display_name="Target Column",
            info="Name of the target column in the DataFrame.",
            required=True,
        ),
        FloatInput(
            name="test_size",
            display_name="Test Size",
            info="Proportion of the dataset to include in the test split (between 0 and 1).",
            value=0.2,
        ),
        DropdownInput(
            name="model_type",
            display_name="Model Type",
            info="Choose a machine learning model to train.",
            options=[
                "LogisticRegression",
                "RandomForestClassifier", 
                "SVC",
                "DecisionTreeClassifier",
                "KNeighborsClassifier",
                "GradientBoostingClassifier",
                "AdaBoostClassifier",
                "GaussianNB",
                "ExtraTreesClassifier",
                "RidgeClassifier",
                "XGBClassifier"
            ],
            value="LogisticRegression",
        ),
    ]

    outputs = [
        Output(name="model", display_name="Trained Model", method="get_model"),
        Output(name="report", display_name="Training Report", method="training_report"),
    ]

    def build(self):
        try:
            df = self.df.copy()
            if self.target_column not in df.columns:
                raise ValueError(f"Target column '{self.target_column}' not found in DataFrame.")

            # Validate test_size
            if not (0.05 <= self.test_size <= 0.95):
                raise ValueError(f"Test size must be between 0.05 and 0.95, got {self.test_size}")

            X = df.drop(columns=[self.target_column])
            y = df[self.target_column]

            # Import train_test_split only when needed
            try:
                from sklearn.model_selection import train_test_split
            except ImportError:
                raise ImportError("scikit-learn is required for model training. Install with: pip install scikit-learn")

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.test_size, random_state=42
            )

            # Import models conditionally based on selection
            if self.model_type == "LogisticRegression":
                try:
                    from sklearn.linear_model import LogisticRegression
                    model = LogisticRegression()
                except ImportError:
                    raise ImportError("scikit-learn is required for LogisticRegression. Install with: pip install scikit-learn")
            elif self.model_type == "RandomForestClassifier":
                try:
                    from sklearn.ensemble import RandomForestClassifier
                    model = RandomForestClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for RandomForestClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "SVC":
                try:
                    from sklearn.svm import SVC
                    model = SVC()
                except ImportError:
                    raise ImportError("scikit-learn is required for SVC. Install with: pip install scikit-learn")
            elif self.model_type == "DecisionTreeClassifier":
                try:
                    from sklearn.tree import DecisionTreeClassifier
                    model = DecisionTreeClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for DecisionTreeClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "KNeighborsClassifier":
                try:
                    from sklearn.neighbors import KNeighborsClassifier
                    model = KNeighborsClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for KNeighborsClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "GradientBoostingClassifier":
                try:
                    from sklearn.ensemble import GradientBoostingClassifier
                    model = GradientBoostingClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for GradientBoostingClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "AdaBoostClassifier":
                try:
                    from sklearn.ensemble import AdaBoostClassifier
                    model = AdaBoostClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for AdaBoostClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "GaussianNB":
                try:
                    from sklearn.naive_bayes import GaussianNB
                    model = GaussianNB()
                except ImportError:
                    raise ImportError("scikit-learn is required for GaussianNB. Install with: pip install scikit-learn")
            elif self.model_type == "ExtraTreesClassifier":
                try:
                    from sklearn.ensemble import ExtraTreesClassifier
                    model = ExtraTreesClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for ExtraTreesClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "RidgeClassifier":
                try:
                    from sklearn.linear_model import RidgeClassifier
                    model = RidgeClassifier()
                except ImportError:
                    raise ImportError("scikit-learn is required for RidgeClassifier. Install with: pip install scikit-learn")
            elif self.model_type == "XGBClassifier":
                try:
                    from xgboost import XGBClassifier
                    model = XGBClassifier()
                except ImportError:
                    raise ImportError("XGBoost is required for XGBClassifier. Install with: pip install xgboost")
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")

            model.fit(X_train, y_train)
            self.model = model
            self.report_data = {
                "X_train_shape": X_train.shape,
                "X_test_shape": X_test.shape,
                "y_train_shape": y_train.shape,
                "y_test_shape": y_test.shape,
                "model_type": self.model_type,
                "dependencies_loaded": True
            }

        except ImportError as e:
            self.status = f"Dependency Error: {e}"
            self.model = None
            self.report_data = {"error": str(e), "error_type": "ImportError"}
        except Exception as e:
            self.status = f"Error: {e}"
            self.model = None
            self.report_data = {"error": str(e)}

    def get_model(self) -> Data:
        if self.model is None:
            return Data(data=self.report_data)
        return Data(data={"model": self.model, "type": self.model_type})

    def training_report(self) -> Data:
        return Data(data=self.report_data)
