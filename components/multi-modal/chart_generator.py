import base64
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Any

from langflow.custom import Component
from langflow.io import (
    HandleInput,
    DataFrameInput,
    IntInput,
    DropdownInput,
    StrInput,
    MessageTextInput,
    FloatInput,
    Output,
)
from langflow.logging.logger import logger
from langflow.schema.data import Data
from langflow.schema.dataframe import DataFrame


class ChartGenerator(Component):
    display_name = "Chart Generator"
    description = "Uses LLM to analyze DataFrame and generate appropriate matplotlib charts automatically."
    icon = "chart-line"
    name = "ChartGenerator"

    inputs = [
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="LLM to use for analyzing DataFrame and generating chart code.",
            input_types=["LanguageModel"],
            required=True,
        ),
        DataFrameInput(
            name="dataframe",
            display_name="DataFrame",
            info="The input DataFrame to visualize.",
            required=True,
        ),
        MessageTextInput(
            name="user_question",
            display_name="User Question",
            info="Optional question about the data that will be answered with a chart. If empty, the component will generate the best possible chart based on the data.",
            value="",
            advanced=False,
        ),
        IntInput(
            name="max_categories",
            display_name="Max Categories",
            info="Maximum number of categories to display in categorical charts. Categories beyond this limit will be grouped as 'Other'.",
            value=10,
            advanced=True,
        ),
        DropdownInput(
            name="chart_style",
            display_name="Chart Style",
            info="Matplotlib or Seaborn style to use for the chart.",
            options=[
                "default",
                "seaborn-white",
                "seaborn-dark",
                "seaborn-whitegrid",
                "seaborn-darkgrid",
                "seaborn-ticks",
                "ggplot",
                "classic",
                "bmh",
                "dark_background",
                "seaborn",
                "seaborn-pastel",
                "seaborn-muted",
                "seaborn-colorblind",
            ],
            value="seaborn-whitegrid",
            advanced=True,
        ),
        StrInput(
            name="chart_title",
            display_name="Chart Title",
            info="Custom title for the chart. If empty, LLM will generate an appropriate title.",
            value="",
            advanced=True,
        ),
        FloatInput(
            name="figure_width",
            display_name="Figure Width",
            info="Width of the figure in inches.",
            value=10.0,
            advanced=True,
        ),
        FloatInput(
            name="figure_height",
            display_name="Figure Height",
            info="Height of the figure in inches.",
            value=6.0,
            advanced=True,
        ),
        IntInput(
            name="dpi",
            display_name="DPI",
            info="Resolution of the output image in dots per inch.",
            value=150,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Chart Image (Base64)", name="chart_image", method="generate_chart"),
        Output(display_name="DataFrame (Base64)", name="dataframe_base64", method="get_dataframe_base64"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._generated_code = None
        self._chart_base64 = None
        self._dataframe_base64 = None

    def _analyze_dataframe(self, df: pd.DataFrame) -> str:
        """Analyze DataFrame structure and return summary for LLM."""
        summary = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_data": df.head(5).to_dict(orient="records"),
            "null_counts": df.isnull().sum().to_dict(),
            "numeric_columns": list(df.select_dtypes(include=['number']).columns),
            "categorical_columns": list(df.select_dtypes(include=['object', 'category']).columns),
            "datetime_columns": list(df.select_dtypes(include=['datetime']).columns),
        }
        
        summary_str = f"""DataFrame Analysis:
- Shape: {summary['shape']} (rows, columns)
- Columns: {summary['columns']}
- Data Types: {summary['dtypes']}
- Numeric Columns: {summary['numeric_columns']}
- Categorical Columns: {summary['categorical_columns']}
- DateTime Columns: {summary['datetime_columns']}
- Null Counts: {summary['null_counts']}
- Sample Data (first 5 rows):
{summary['sample_data']}
"""
        return summary_str

    def _get_style_code(self, chart_style: str) -> str:
        """Get the correct style setting code based on chart style."""
        if chart_style.startswith("seaborn-"):
            # Extract seaborn style name (remove "seaborn-" prefix)
            seaborn_style = chart_style.replace("seaborn-", "")
            if seaborn_style in ["white", "dark", "whitegrid", "darkgrid", "ticks", "pastel", "muted", "colorblind"]:
                return f"sns.set_style('{seaborn_style}')"
            else:
                return "sns.set_style('whitegrid')"  # Default seaborn style
        elif chart_style == "default":
            return "# Using default matplotlib style"
        else:
            # Matplotlib style
            return f"plt.style.use('{chart_style}')"

    def _generate_chart_code(self, llm, df_summary: str, user_question: str, max_categories: int, chart_style: str, chart_title: str, figure_width: float, figure_height: float, dpi: int) -> str:
        """Use LLM to generate Python code for creating an appropriate chart."""
        style_code = self._get_style_code(chart_style)
        
        # Build prompt based on whether user provided a question
        if user_question and user_question.strip():
            question_context = f"""
USER QUESTION: {user_question.strip()}

Your task is to answer this question by creating an appropriate chart that visualizes the answer.
The chart should directly address the user's question using the available data.
"""
        else:
            question_context = """
Your task is to create the best possible chart that provides meaningful insights from the data.
Choose the most appropriate visualization that highlights key patterns, trends, or relationships in the data.
"""
        
        prompt = f"""You are a data visualization expert. Analyze the following DataFrame and generate Python code to create an appropriate matplotlib chart.

DataFrame Summary:
{df_summary}

{question_context}

Requirements:
1. Use matplotlib and seaborn libraries
2. Set style using: {style_code}
3. Figure size: ({figure_width}, {figure_height})
4. DPI: {dpi}
5. Maximum categories to display: {max_categories} (group others as 'Other')
6. Chart title: {"(generate appropriate title based on the question or data)" if not chart_title else chart_title}
7. The DataFrame variable is named 'df'
8. The code must save the figure to a BytesIO buffer and encode as base64
9. Return ONLY the Python code, no explanations or markdown formatting
10. The code should be complete and executable
11. Choose the most appropriate chart type based on the data and question (bar, line, scatter, histogram, box, heatmap, etc.)
12. Handle categorical data by limiting to max_categories and grouping the rest
13. Make the chart visually appealing with proper labels, legends, and formatting
14. IMPORTANT: Use the style setting code exactly as provided: {style_code}
15. After creating the chart, save it to a BytesIO buffer and encode as base64
16. Set the result to a variable named 'chart_base64'
17. The chart should clearly answer the user's question (if provided) or show the most important insights from the data

Generate the Python code:"""

        try:
            # Use the LLM to generate code
            if hasattr(llm, 'invoke'):
                response = llm.invoke(prompt)
                if hasattr(response, 'content'):
                    code = response.content.strip()
                else:
                    code = str(response).strip()
            else:
                code = str(llm(prompt)).strip()
            
            # Clean up the code - remove markdown code blocks if present
            if code.startswith("```python"):
                code = code[9:]
            elif code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            
            code = code.strip()
            
            # Validate that code contains necessary imports and operations
            if "matplotlib" not in code and "plt" not in code:
                raise ValueError("Generated code does not include matplotlib")
            
            if "base64" not in code:
                raise ValueError("Generated code does not include base64 encoding")
            
            return code
            
        except Exception as e:
            error_msg = f"Error generating chart code: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_chart_code(self, code: str, df: pd.DataFrame, chart_style: str) -> str:
        """Execute the generated code and return base64 encoded image."""
        try:
            # Apply style before executing code
            style_code = self._get_style_code(chart_style)
            if style_code.startswith("sns."):
                # Execute seaborn style
                exec(style_code, {'sns': sns})
            elif not style_code.startswith("#"):
                # Execute matplotlib style
                exec(style_code, {'plt': plt})
            
            # Prepare execution environment
            exec_globals = {
                'pd': pd,
                'plt': plt,
                'sns': sns,
                'df': df,
                'base64': base64,
                'io': io,
                'BytesIO': io.BytesIO,
            }
            
            # Execute the code
            exec(code, exec_globals)
            
            # The code should set a variable 'chart_base64' or 'image_base64'
            if 'chart_base64' in exec_globals:
                return exec_globals['chart_base64']
            elif 'image_base64' in exec_globals:
                return exec_globals['image_base64']
            elif 'base64_image' in exec_globals:
                return exec_globals['base64_image']
            else:
                # Try to find any variable containing base64
                for key, value in exec_globals.items():
                    if isinstance(value, str) and len(value) > 100 and value.startswith(('data:image', 'iVBORw0KGgo')):
                        return value
                
                raise ValueError("Generated code did not produce a base64 encoded image. Code should set 'chart_base64' variable.")
            
        except Exception as e:
            error_msg = f"Error executing chart code: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Generated code:\n{code}")
            raise RuntimeError(error_msg) from e

    def _dataframe_to_base64(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to base64 encoded image."""
        try:
            fig, ax = plt.subplots(figsize=(len(df.columns) * 1.2, max(len(df) * 0.3, 4)))
            ax.axis("tight")
            ax.axis("off")
            
            # Create table
            table = ax.table(
                cellText=df.head(100).values,  # Limit to first 100 rows
                colLabels=df.columns,
                loc='center',
                cellLoc='left'
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.5)
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            plt.close(fig)
            buf.seek(0)
            
            base64_image = base64.b64encode(buf.read()).decode('utf-8')
            return base64_image
            
        except Exception as e:
            error_msg = f"Error converting DataFrame to base64: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def generate_chart(self) -> Data:
        """Generate chart using LLM analysis and return as base64."""
        llm = getattr(self, "llm", None)
        dataframe = getattr(self, "dataframe", None)
        
        # Validate inputs
        if not llm:
            error_msg = "No LLM provided"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})
        
        if dataframe is None:
            error_msg = "No DataFrame provided"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})
        
        # Convert to pandas DataFrame
        try:
            df = pd.DataFrame(dataframe)
        except Exception as e:
            error_msg = f"Error converting to pandas DataFrame: {str(e)}"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})
        
        if df.empty:
            error_msg = "DataFrame is empty"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})
        
        try:
            # Analyze DataFrame
            self.status = "Analyzing DataFrame..."
            logger.info("Analyzing DataFrame structure")
            df_summary = self._analyze_dataframe(df)
            
            # Get parameters
            user_question = getattr(self, "user_question", "")
            max_categories = getattr(self, "max_categories", 10)
            chart_style = getattr(self, "chart_style", "seaborn-whitegrid")
            chart_title = getattr(self, "chart_title", "")
            figure_width = getattr(self, "figure_width", 10.0)
            figure_height = getattr(self, "figure_height", 6.0)
            dpi = getattr(self, "dpi", 150)
            
            # Generate chart code using LLM
            if user_question and user_question.strip():
                self.status = f"Generating chart code to answer: {user_question[:50]}..."
                logger.info(f"Generating chart code to answer user question: {user_question}")
            else:
                self.status = "Generating best possible chart code..."
                logger.info("Generating best possible chart code based on data")
            
            code = self._generate_chart_code(
                llm, df_summary, user_question, max_categories, chart_style, 
                chart_title, figure_width, figure_height, dpi
            )
            self._generated_code = code
            
            # Execute code to generate chart
            self.status = "Executing chart code..."
            logger.info("Executing generated chart code")
            chart_base64 = self._execute_chart_code(code, df, chart_style)
            self._chart_base64 = chart_base64
            
            # Create markdown URL format
            markdown_url = f"![Chart](data:image/png;base64,{chart_base64})"
            
            self.status = "✅ Chart generated successfully"
            logger.info("Chart generated successfully")
            
            return Data(data={
                "chart_base64": chart_base64,
                "markdown_url": markdown_url,
                "code": code,
            })
            
        except Exception as e:
            error_msg = f"Error generating chart: {str(e)}"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})

    def get_dataframe_base64(self) -> Data:
        """Convert DataFrame to base64 encoded image."""
        dataframe = getattr(self, "dataframe", None)
        
        if dataframe is None:
            error_msg = "No DataFrame provided"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})
        
        try:
            # Convert to pandas DataFrame
            df = pd.DataFrame(dataframe)
            
            if df.empty:
                error_msg = "DataFrame is empty"
                self.status = f"❌ {error_msg}"
                logger.error(error_msg)
                return Data(data={"error": error_msg})
            
            # Convert to base64
            self.status = "Converting DataFrame to base64..."
            logger.info("Converting DataFrame to base64 image")
            dataframe_base64 = self._dataframe_to_base64(df)
            self._dataframe_base64 = dataframe_base64
            
            # Create markdown URL format
            markdown_url = f"![DataFrame](data:image/png;base64,{dataframe_base64})"
            
            self.status = "✅ DataFrame converted to base64"
            logger.info("DataFrame converted to base64 successfully")
            
            return Data(data={
                "dataframe_base64": dataframe_base64,
                "markdown_url": markdown_url,
            })
            
        except Exception as e:
            error_msg = f"Error converting DataFrame to base64: {str(e)}"
            self.status = f"❌ {error_msg}"
            logger.error(error_msg)
            return Data(data={"error": error_msg})

