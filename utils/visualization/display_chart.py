"""
SQL 쿼리 결과를 Plotly로 시각화하는 모듈

이 모듈은 Lang2SQL 실행 결과를 다양한 형태의 차트로 시각화하는 기능을 제공합니다.
LLM을 활용하여 적절한 Plotly 코드를 생성하고 실행합니다.
"""

import os
import re
from typing import Optional

import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class DisplayChart:
    """
    SQL쿼리가 실행된 결과를 그래프로 시각화하는 Class입니다.

    쿼리 결과를 비롯한 유저 질문, sql를 prompt에 입력하여
    plotly코드를 출력하여 excute한 결과를 fig 객체로 반환합니다.
    """

    def __init__(self, question: str, sql: str, df_metadata: str):
        """
        DisplayChart 인스턴스를 초기화합니다.

        Args:
            question (str): 사용자 질문
            sql (str): 실행된 SQL 쿼리
            df_metadata (str): 데이터프레임 메타데이터
        """
        self.question = question
        self.sql = sql
        self.df_metadata = df_metadata

    def llm_model_for_chart(self, message_log) -> Optional[str]:
        """
        LLM 모델을 사용하여 차트 생성 코드를 생성합니다.

        Args:
            message_log: LLM에 전달할 메시지 목록

        Returns:
            Optional[str]: 생성된 차트 코드 또는 None
        """
        provider = os.getenv("LLM_PROVIDER")
        if provider == "openai":
            llm = ChatOpenAI(
                model=os.getenv("OPEN_AI_LLM_MODEL", "gpt-4o"),
                api_key=os.getenv("OPEN_AI_KEY"),
            )
            result = llm.invoke(message_log)
            return result
        return None

    def _extract_python_code(self, markdown_string: str) -> str:
        """
        마크다운 문자열에서 Python 코드 블록을 추출합니다.

        Args:
            markdown_string: 마크다운 형식의 문자열

        Returns:
            str: 추출된 Python 코드
        """
        # Strip whitespace to avoid indentation errors in LLM-generated code
        if hasattr(markdown_string, "content"):
            markdown_string = markdown_string.content.split("```")[1][6:].strip()
        else:
            markdown_string = str(markdown_string)

        # Regex pattern to match Python code blocks
        pattern = r"```[\w\s]*python\n([\s\S]*?)```|```([\s\S]*?)```"

        # Find all matches in the markdown string
        matches = re.findall(pattern, markdown_string, re.IGNORECASE)

        # Extract the Python code from the matches
        python_code = []
        for match in matches:
            python = match[0] if match[0] else match[1]
            python_code.append(python.strip())

        if len(python_code) == 0:
            return markdown_string

        return python_code[0]

    def _sanitize_plotly_code(self, raw_plotly_code: str) -> str:
        """
        Plotly 코드에서 불필요한 부분을 제거합니다.

        Args:
            raw_plotly_code: 원본 Plotly 코드

        Returns:
            str: 정리된 Plotly 코드
        """
        # Remove the fig.show() statement from the plotly code
        plotly_code = raw_plotly_code.replace("fig.show()", "")
        return plotly_code

    def generate_plotly_code(self) -> str:
        """
        LLM을 사용하여 Plotly 코드를 생성합니다.

        Returns:
            str: 생성된 Plotly 코드
        """
        if self.question is not None:
            system_msg = f"The following is a pandas DataFrame that contains the results of the query that answers the question the user asked: '{self.question}'"
        else:
            system_msg = "The following is a pandas DataFrame "

        if self.sql is not None:
            system_msg += (
                f"\n\nThe DataFrame was produced using this query: {self.sql}\n\n"
            )

        system_msg += f"The following is information about the resulting pandas DataFrame 'df': \n{self.df_metadata}"

        message_log = [
            SystemMessage(content=system_msg),
            HumanMessage(
                content="Can you generate the Python plotly code to chart the results of the dataframe? Assume the data is in a pandas dataframe called 'df'. If there is only one value in the dataframe, use an Indicator. Respond with only Python code. Do not answer with any explanations -- just the code."
            ),
        ]

        plotly_code = self.llm_model_for_chart(message_log)
        if plotly_code is None:
            return ""

        return self._sanitize_plotly_code(self._extract_python_code(plotly_code))

    def get_plotly_figure(
        self, plotly_code: str, df: pd.DataFrame, dark_mode: bool = True
    ) -> Optional[plotly.graph_objs.Figure]:
        """
        Plotly 코드를 실행하여 Figure 객체를 생성합니다.

        Args:
            plotly_code: 실행할 Plotly 코드
            df: 데이터프레임
            dark_mode: 다크 모드 사용 여부

        Returns:
            Optional[plotly.graph_objs.Figure]: 생성된 Figure 객체 또는 None
        """
        ldict = {"df": df, "px": px, "go": go}
        fig = None

        try:
            exec(plotly_code, globals(), ldict)  # noqa: S102
            fig = ldict.get("fig", None)

        except Exception:
            # Inspect data types
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            categorical_cols = df.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()

            # Decision-making for plot type
            if len(numeric_cols) >= 2:
                # Use the first two numeric columns for a scatter plot
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])
            elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
                # Use a bar plot if there's one numeric and one categorical column
                fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0])
            elif len(categorical_cols) >= 1 and df[categorical_cols[0]].nunique() < 10:
                # Use a pie chart for categorical data with fewer unique values
                fig = px.pie(df, names=categorical_cols[0])
            else:
                # Default to a simple line plot if above conditions are not met
                fig = px.line(df)

        if fig is None:
            return None

        if dark_mode:
            fig.update_layout(template="plotly_dark")

        return fig
