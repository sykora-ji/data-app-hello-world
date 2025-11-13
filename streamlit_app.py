import streamlit as st
import toml
import os


def display_toml_content(title: str, file_path: str) -> None:
    """Render TOML file content in Streamlit."""
    st.title(title)
    try:
        content = toml.load(file_path)
        st.write(content)
    except FileNotFoundError:
        st.error(f'Soubor {file_path} nebyl nalezen.')
    except toml.TomlDecodeError:
        st.error(f'Soubor {file_path} má neplatný formát.')

tabs = st.tabs(["Hello world", "Debug"])

with tabs[0]:
    st.header("Hello World App")
    st.write("Hello, world! Toto je tvoje první aplikace ve Streamlit.")

    name = st.text_input("Zadej své jméno:")

    if st.button("Pozdrav"):
        st.write(f"Ahoj, {name}!")

with tabs[1]:
    st.header("Debug")

    config_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'config.toml')
    secrets_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'secrets.toml')

    st.title('Current path')
    st.write(os.path.dirname(__file__))

    st.title('Current working directory')
    st.write(os.getcwd())

    display_toml_content('Obsah config.toml', config_file_path)
    display_toml_content('Obsah secrets.toml', secrets_file_path)

