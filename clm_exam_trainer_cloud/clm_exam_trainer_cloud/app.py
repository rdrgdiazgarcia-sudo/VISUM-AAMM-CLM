
import streamlit as st
import pandas as pd
import random, os, uuid

DATA_DIR = "data"
IMAGES_DIR = "images"
SPECIES_CSV = os.path.join(DATA_DIR, "species.csv")
SPECIES_TEMPLATE = os.path.join(DATA_DIR, "species_template.csv")
MAPPING_CSV = os.path.join(DATA_DIR, "image_species_mapping.csv")

st.set_page_config(page_title="CLM AAMM Trainer", page_icon="🌿", layout="wide")
st.title("🌿 Entrenador práctico AAMM Castilla-La Mancha (imágenes)")

with st.expander("📌 Cómo empezar"):
    st.markdown("""
    1. Este proyecto ya está listo para Streamlit Cloud.  
    2. Edita `data/species.csv` para ampliar tu banco (cinegéticas, EEI, pescables, CREA, tallas...).  
    3. Sube imágenes a la carpeta `images/` (en la nube podrás arrastrarlas mediante el uploader) y vincúlalas.  
    4. Ve a **Modo Quiz** para practicar.
    """)

@st.cache_data
def load_species():
    path = SPECIES_CSV if os.path.exists(SPECIES_CSV) else SPECIES_TEMPLATE
    df = pd.read_csv(path, comment="#", dtype=str).fillna("")
    needed = ["id","common_name","scientific_name","group","crea_category","is_invasive","is_cinegetica",
              "cinegetica_comercializable_vivo","cinegetica_comercializable_muerto","has_hunting_quota",
              "is_pescable","pescable_tipo","talla_minima_mm","notas"]
    for c in needed:
        if c not in df.columns:
            df[c] = ""
    for i, row in df.iterrows():
        if not row["id"]:
            base = (row.get("scientific_name") or row.get("common_name") or f"sp{i}").lower().replace(" ", "_")
            df.at[i, "id"] = f"{base}_{uuid.uuid4().hex[:6]}"
    return df

@st.cache_data
def load_mapping():
    if not os.path.exists(MAPPING_CSV):
        return pd.DataFrame(columns=["image_filename","species_id","scientific_name","common_name"])
    return pd.read_csv(MAPPING_CSV, comment="#", dtype=str).fillna("")

species_df = load_species()
mapping_df = load_mapping()

tab1, tab2, tab3 = st.tabs(["📚 Base de especies", "🖼️ Cargar imágenes y vincular", "🧠 Modo Quiz"])

with tab1:
    st.subheader("Base de especies (CSV)")
    st.write("Edita `data/species.csv` (cinegéticas, EEI, pescables, CREA, tallas, cupos…).")
    st.dataframe(species_df, use_container_width=True)
    if os.path.exists(SPECIES_TEMPLATE):
        st.download_button("⬇️ Descargar plantilla species_template.csv", data=open(SPECIES_TEMPLATE,"rb").read(), file_name="species_template.csv")

with tab2:
    st.subheader("Sube imágenes y vincula")
    upl = st.file_uploader("Arrastra tus imágenes", type=["jpg","jpeg","png","webp"], accept_multiple_files=True)
    if upl:
        for f in upl:
            with open(os.path.join(IMAGES_DIR, f.name), "wb") as out:
                out.write(f.read())
        st.success(f"Guardadas {len(upl)} imagen(es).")

    st.markdown("### Vincular imágenes con especies")
    imgs = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".webp"))])
    if not imgs:
        st.info("Coloca imágenes en /images para empezar.")
    else:
        image_name = st.selectbox("Imagen", imgs)
        st.image(os.path.join(IMAGES_DIR, image_name), use_column_width=True)

        def label(row):
            common = row.get("common_name","")
            sci = row.get("scientific_name","")
            return f"{common} — {sci}".strip(" —")
        options = [{"key": row["id"], "label": label(row)} for _, row in species_df.iterrows()]
        chosen = st.selectbox("Especie", options, format_func=lambda o: o["label"])

        if st.button("➕ Guardar vínculo"):
            new_row = {"image_filename": image_name, "species_id": chosen["key"], "scientific_name":"", "common_name":""}
            mapping_tmp = load_mapping()
            mapping_tmp.loc[len(mapping_tmp)] = new_row
            mapping_tmp.to_csv(MAPPING_CSV, index=False)
            st.success("Vínculo guardado.")
            st.cache_data.clear()

        st.markdown("#### Vínculos existentes")
        st.dataframe(load_mapping(), use_container_width=True)

with tab3:
    st.subheader("Generador de preguntas tipo examen")
    st.markdown("Elige tipos de pregunta y número total.")

    q_types = st.multiselect("Tipos de pregunta", [
        "Identificación (nombre científico)",
        "Identificación (nombre vulgar)",
        "¿Es exótica invasora (EEI)?",
        "Categoría CREA",
        "¿Es cinegética?",
        "Cinegética: ¿comercializable en vivo?",
        "Cinegética: ¿comercializable en muerto?",
        "Cinegética: ¿tiene cupo?",
        "¿Es pescable?",
        "Pescables: tipo (talla/EEI/No)",
        "Pescables: talla mínima (numérica)"
    ], default=[
        "Identificación (nombre científico)",
        "¿Es exótica invasora (EEI)?",
        "Categoría CREA",
        "Pescables: tipo (talla/EEI/No)"
    ])

    num_q = st.slider("Número total de preguntas", 1, 50, 12)

    def yn(flag):
        return "Sí" if str(flag).strip().upper() == "TRUE" else "No"

    def build_question(img_row, sp, qtype):
        img_path = os.path.join(IMAGES_DIR, img_row["image_filename"])

        if qtype == "Identificación (nombre científico)":
            correct = sp.get("scientific_name","").strip()
            same = species_df[species_df["group"] == sp.get("group","")]
            pool = [x for x in same["scientific_name"].tolist() if x and x != correct]
            random.shuffle(pool)
            distractors = (pool[:3] if len(pool) >= 3 else [x for x in species_df["scientific_name"].tolist() if x and x != correct][:3])
            while len(distractors) < 3: distractors.append("—")
            opts = distractors + [correct]; random.shuffle(opts)
            enun = "Observa la imagen y señala el **nombre científico** correcto:"
            exp = f"Es **{sp.get('common_name','')}** (*{correct}*)."
            return enun, opts, correct, exp, img_path

        if qtype == "Identificación (nombre vulgar)":
            correct = sp.get("common_name","").strip()
            pool = [x for x in species_df["common_name"].tolist() if x and x != correct]
            random.shuffle(pool)
            distractors = pool[:3]
            while len(distractors) < 3: distractors.append("—")
            opts = distractors + [correct]; random.shuffle(opts)
            enun = "Observa la imagen y señala el **nombre vulgar** correcto:"
            exp = f"Nombre vulgar correcto: **{correct}**."
            return enun, opts, correct, exp, img_path

        if qtype == "¿Es exótica invasora (EEI)?":
            correct = yn(sp.get("is_invasive",""))
            opts = ["Sí","No","Solo en ZEPA","Solo en humedales protegidos"]
            enun = "En Castilla-La Mancha, ¿está considerada **especie exótica invasora (EEI)**?"
            exp = f"En tu base: EEI = {sp.get('is_invasive','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "Categoría CREA":
            correct = (sp.get("crea_category","") or "Sin categoría")
            pool = ["en peligro de extinción","vulnerable","de interés especial","sensible a la alteración del hábitat","Sin categoría"]
            if correct not in pool: pool.append(correct)
            random.shuffle(pool); opts = pool[:4]
            if correct not in opts: opts[-1] = correct; random.shuffle(opts)
            enun = "¿Cuál es la **categoría CREA** de la especie en CLM?"
            exp = f"En tu base figura como: **{correct}**."
            return enun, opts, correct, exp, img_path

        if qtype == "¿Es cinegética?":
            correct = yn(sp.get("is_cinegetica",""))
            opts = ["Sí","No","Solo por control de daños","Solo en reservas nacionales"]
            enun = "En Castilla-La Mancha, ¿esta especie es **cinegética**?"
            exp = f"is_cinegetica = {sp.get('is_cinegetica','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "Cinegética: ¿comercializable en vivo?":
            correct = yn(sp.get("cinegetica_comercializable_vivo",""))
            opts = ["Sí","No","Solo en media veda","Solo con autorización excepcional"]
            enun = "Según la Orden de Vedas que reflejes en tu base, ¿es **comercializable en vivo**?"
            exp = f"cinegetica_comercializable_vivo = {sp.get('cinegetica_comercializable_vivo','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "Cinegética: ¿comercializable en muerto?":
            correct = yn(sp.get("cinegetica_comercializable_muerto",""))
            opts = ["Sí","No","Solo en media veda","Solo en controles excepcionales"]
            enun = "Según la Orden de Vedas que reflejes en tu base, ¿es **comercializable en muerto**?"
            exp = f"cinegetica_comercializable_muerto = {sp.get('cinegetica_comercializable_muerto','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "Cinegética: ¿tiene cupo?":
            correct = yn(sp.get("has_hunting_quota",""))
            opts = ["Sí","No","Solo en ZEPA","Solo en reservas nacionales"]
            enun = "¿Tiene **cupo de extracción** (según Orden de Vedas que indiques en tu base)?"
            exp = f"has_hunting_quota = {sp.get('has_hunting_quota','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "¿Es pescable?":
            correct = yn(sp.get("is_pescable",""))
            opts = ["Sí","No","Solo en cotos intensivos","Solo captura y suelta"]
            enun = "En aguas continentales de CLM, ¿esta especie es **pescable**?"
            exp = f"is_pescable = {sp.get('is_pescable','')}."
            return enun, opts, correct, exp, img_path

        if qtype == "Pescables: tipo (talla/EEI/No)":
            correct = sp.get("pescable_tipo","—") or "—"
            pool = ["talla mínima","EEI pescable","EEI no pescable","no pescable","—"]
            random.shuffle(pool); opts = pool[:4]
            if correct not in opts:
                opts[-1] = correct; random.shuffle(opts)
            enun = "Marca el **tipo** aplicable: talla mínima / EEI pescable / EEI no pescable / no pescable."
            exp = f"pescable_tipo = **{correct}**."
            return enun, opts, correct, exp, img_path

        if qtype == "Pescables: talla mínima (numérica)":
            correct = sp.get("talla_minima_mm","").strip() or "—"
            opts = set()
            if correct.isdigit():
                c = int(correct)
                for k in [-20, -10, +10, +20, +30, -30]:
                    val = str(max(0, c + k))
                    if val != correct:
                        opts.add(val)
                opts = list(opts)[:3]
            else:
                opts = ["—","0","10"]
            while len(opts) < 3: opts.append("—")
            options = opts + [correct]
            random.shuffle(options)
            enun = "Indica la **talla mínima** (en mm) aplicable a la especie (si procede)."
            exp = f"talla_minima_mm = **{correct}**."
            return enun, options, correct, exp, img_path

        return "","", "", "", None

    if st.button("🎯 Empezar quiz"):
        pairs = []
        for _, m in load_mapping().iterrows():
            sp_row = None
            if m["species_id"]:
                g = species_df[species_df["id"] == m["species_id"]]
                if not g.empty: sp_row = g.iloc[0].to_dict()
            if sp_row is None and m.get("scientific_name",""):
                g = species_df[species_df["scientific_name"].str.lower() == m["scientific_name"].lower()]
                if not g.empty: sp_row = g.iloc[0].to_dict()
            if sp_row is None and m.get("common_name",""):
                g = species_df[species_df["common_name"].str.lower() == m["common_name"].lower()]
                if not g.empty: sp_row = g.iloc[0].to_dict()
            if sp_row is not None and os.path.exists(os.path.join(IMAGES_DIR, m["image_filename"])):
                pairs.append((m, sp_row))

        if not pairs:
            st.warning("No hay vínculos imagen-especie. Añade al menos uno en la pestaña anterior.")
        else:
            questions = []
            qtypes_available = q_types if q_types else ["Identificación (nombre científico)"]
            while len(questions) < num_q:
                m, sp = random.choice(pairs)
                qtype = random.choice(qtypes_available)
                enun, opts, corr, exp, img_path = build_question(m, sp, qtype)
                if enun:
                    questions.append({"img": img_path, "qtype": qtype, "q": enun, "opts": opts, "correct": corr, "exp": exp})
            st.session_state["questions"] = questions
            st.session_state["answers"] = [None]*len(questions)
            st.success(f"Se generaron {len(questions)} preguntas. ¡Suerte!")

    questions = st.session_state.get("questions", [])
    answers = st.session_state.get("answers", [])

    if questions:
        for i, q in enumerate(questions):
            st.markdown("---")
            cols = st.columns([2,3])
            with cols[0]:
                if q["img"] and os.path.exists(q["img"]):
                    st.image(q["img"], use_column_width=True)
                st.caption(q["qtype"])
            with cols[1]:
                st.markdown(f"**Pregunta {i+1}.** {q['q']}")
                choice = st.radio("Elige una opción:", q["opts"], index=None, key=f"q{i}")
                answers[i] = choice

        if st.button("✅ Corregir"):
            correct_count = 0
            for i, q in enumerate(questions):
                user = answers[i]
                ok = (user == q["correct"])
                if ok: correct_count += 1
                st.markdown(f"**Pregunta {i+1}:** {'✅ Correcta' if ok else '❌ Incorrecta'}")
                st.markdown(f"- Respuesta correcta: **{q['correct']}**")
                st.markdown(f"- Explicación: {q['exp']}")
            st.markdown(f"### Puntuación: {correct_count} / {len(questions)}")
