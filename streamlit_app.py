import streamlit as st
import toml
import os
import sys
import json
import importlib.metadata
import pandas as pd


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


def render_file_preview(file_path: str) -> None:
    """Render a preview of the file based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.csv':
            st.dataframe(pd.read_csv(file_path))
        elif ext == '.tsv':
            st.dataframe(pd.read_csv(file_path, sep='\t'))
        elif ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                st.json(json.load(f))
        elif ext == '.toml':
            st.write(toml.load(file_path))
        elif ext in ('.txt', '.log', '.md', '.yaml', '.yml', '.xml', '.html', '.py', '.sql', '.ini', '.cfg', '.conf'):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                st.code(f.read(), language=ext.lstrip('.') or None)
        else:
            size = os.path.getsize(file_path)
            st.info(f'Náhled pro příponu {ext or "(žádná)"} není podporován. Velikost: {size} B.')
    except Exception as e:
        st.error(f'Chyba při čtení souboru: {e}')

tabs = st.tabs(["Hello world", "Debug"])

with tabs[0]:
    st.header("Hello World App")
    st.write("Hello, world! Toto je tvoje první aplikace ve Streamlit.")

    name = st.text_input("Zadej své jméno:")

    if st.button("Pozdrav"):
        st.write(f"Ahoj, {name}!")

with tabs[1]:
    st.header("Debug")
    st.title('Python version')
    st.write(sys.version)

    config_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'config.toml')
    secrets_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'secrets.toml')

    st.title('Current path')
    st.write(os.path.dirname(__file__))

    st.title('Current working directory')
    st.write(os.getcwd())

    display_toml_content('Obsah config.toml', config_file_path)
    display_toml_content('Obsah secrets.toml', secrets_file_path)

    st.title('Installed packages')
    for dist in importlib.metadata.distributions():
        st.write(dist.metadata["Name"], dist.version)

    st.title('Soubory v /data')
    data_path = '/data'
    if os.path.isdir(data_path):
        files = []
        for root, _, filenames in os.walk(data_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        if files:
            for file_path in sorted(files):
                with st.expander(file_path):
                    render_file_preview(file_path)
        else:
            st.write(f'Složka {data_path} je prázdná.')
    else:
        st.error(f'Složka {data_path} neexistuje.')

