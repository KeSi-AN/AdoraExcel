import streamlit as st
import pandas as pd
import plotly.express as px
import io

def visualize_excel_file():
    """
    Streamlit interface for uploading and visualizing Excel files.
    Allows selecting sheets, chart types, X-axis, and Y-axis
    to generate interactive Plotly charts.
    """
    st.header("Visualize Excel")

    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Read the Excel file
            excel_data = pd.ExcelFile(uploaded_file)

            # Get sheet names
            sheet_names = excel_data.sheet_names

            selected_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox("Select a sheet", sheet_names)

            df = excel_data.parse(selected_sheet)

            st.subheader("Data Preview (first 5 rows)")
            st.write(df.head())

            # Identify column types
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            object_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            all_cols = df.columns.tolist()

            st.subheader("Chart Options")

            chart_type = st.selectbox(
                "Select chart type",
                ["Bar", "Line", "Pie", "Scatter"]
            )

            x_axis = st.selectbox("Select X-axis", all_cols)
            y_axis = st.selectbox("Select Y-axis", all_cols)

            if st.button("Generate Chart"):
                try:
                    fig = None
                    if chart_type == "Bar":
                        if x_axis in all_cols and y_axis in all_cols:
                            fig = px.bar(df, x=x_axis, y=y_axis, title=f'{chart_type} Chart of {y_axis} vs {x_axis}')
                        else:
                             st.warning("Please select valid X and Y axes for the bar chart.")
                    elif chart_type == "Line":
                         if x_axis in all_cols and y_axis in all_cols:
                            fig = px.line(df, x=x_axis, y=y_axis, title=f'{chart_type} Chart of {y_axis} vs {x_axis}')
                         else:
                             st.warning("Please select valid X and Y axes for the line chart.")
                    elif chart_type == "Pie":
                         if y_axis in numeric_cols and x_axis in object_cols:
                            fig = px.pie(df, values=y_axis, names=x_axis, title=f'{chart_type} Chart of {y_axis} by {x_axis}')
                         else:
                              st.warning("For Pie chart, please select a numeric column for 'Values' (Y-axis) and a categorical column for 'Names' (X-axis).")
                    elif chart_type == "Scatter":
                         if x_axis in all_cols and y_axis in all_cols:
                            fig = px.scatter(df, x=x_axis, y=y_axis, title=f'{chart_type} Chart of {y_axis} vs {x_axis}')
                         else:
                             st.warning("Please select valid X and Y axes for the scatter chart.")

                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"An error occurred while generating the chart: {e}")

        except Exception as e:
            st.error(f"Error reading the Excel file: {e}")