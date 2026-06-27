import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
st.set_page_config(
    page_title="La Pollada",
    page_icon="⚽",
    layout="wide"
)

# -----------------------------
# Cargar datos
# -----------------------------
API_URL = "https://script.google.com/macros/s/AKfycbyC5g4hOzBMkoC9YxLj_gadcljHmqVsfIidI0L3GKb5u5bS0ccrlE3l-LqMAaes3KPNjA/exec"


def leer_sheet(nombre_hoja):
    try:
        respuesta = requests.get(
            API_URL,
            params={
                "action": "read",
                "sheet": nombre_hoja
            },
            timeout=30
        )
    except requests.exceptions.RequestException:
        st.warning(
            "⚠️ Google Sheets tardó demasiado en responder. "
            "Refresca la página e intenta de nuevo."
        )
        return pd.DataFrame()

    try:
        datos = respuesta.json()
    except Exception:
        st.warning(
            "⚠️ No se pudieron cargar datos de Google Sheets. "
            "Refresca la página e intenta de nuevo."
        )
        return pd.DataFrame()

    return pd.DataFrame(datos)

    try:
        datos = respuesta.json()
    except Exception:
        st.warning("⚠️ No se pudieron cargar datos de Google Sheets. Refresca la página e intenta de nuevo.")
        return pd.DataFrame()

    return pd.DataFrame(datos)


def escribir_sheet(nombre_hoja, df):
    filas = df.to_dict(orient="records")

    try:
        respuesta = requests.post(
            API_URL,
            json={
                "action": "write",
                "sheet": nombre_hoja,
                "rows": filas
            },
            timeout=30
        )
    except requests.exceptions.RequestException:
        st.error("⚠️ No se pudo conectar con Google Sheets. Intenta de nuevo.")
        st.stop()

    try:
        return respuesta.json()
    except Exception:
        if respuesta.status_code == 200:
            return {"status": "ok"}
        else:
            st.error("⚠️ Google Sheets respondió con error.")
            st.write(respuesta.text[:500])
            st.stop()
def cargar_jugadores():
    return leer_sheet("jugadores")


def cargar_partidos():
    df = leer_sheet("partidos")

    columnas = [
        "id",
        "jornada",
        "equipo_local",
        "equipo_visitante",
        "fecha"
    ]

    if df.empty:
        return pd.DataFrame(columns=columnas)

    return df

def cargar_resultados():
    df = leer_sheet("resultados")

    if df.empty:
        return pd.DataFrame(columns=[
            "partido_id", "goles_local", "goles_visitante"
        ])

    return df
def guardar_resultado(partido_id, goles_local, goles_visitante):

    resultados = cargar_resultados()

    if resultados.empty:
        st.error(
            "⚠️ Error de seguridad: no se cargaron los resultados existentes. "
            "No se guardó nada para evitar borrar datos."
        )
        st.stop()

    nueva_fila = pd.DataFrame([
        {
            "partido_id": partido_id,
            "goles_local": goles_local,
            "goles_visitante": goles_visitante
        }
    ])

    resultados = resultados[
        resultados["partido_id"] != partido_id
    ]

    resultados = pd.concat(
        [resultados, nueva_fila],
        ignore_index=True
    )

    escribir_sheet("resultados", resultados)
def eliminar_resultado(partido_id):

    resultados = cargar_resultados()

    resultados = resultados[
        resultados["partido_id"] != partido_id
    ]

    escribir_sheet("resultados", resultados)
def cargar_pronosticos():
    df = leer_sheet("pronosticos")

    if df.empty:
        return pd.DataFrame(columns=[
            "usuario", "partido_id", "equipo_local", "equipo_visitante",
            "goles_local", "goles_visitante"
        ])

    return df
def cargar_predicciones_especiales():
    df = leer_sheet("predicciones_especiales")

    if df.empty:
        return pd.DataFrame(columns=[
            "usuario",
            "campeon",
            "subcampeon",
            "tercer_lugar",
            "maximo_goleador",
            "mejor_jugador",
            "mejor_arquero"
        ])

    return df


def guardar_predicciones_especiales(usuario, predicciones):
    df_existente = cargar_predicciones_especiales()

    df_existente = df_existente[
        df_existente["usuario"] != usuario
    ]

    df_nuevo = pd.DataFrame([predicciones])

    df_final = pd.concat(
        [df_existente, df_nuevo],
        ignore_index=True
    )

    escribir_sheet("predicciones_especiales", df_final)

def guardar_pronosticos(nuevos_pronosticos):
    df_nuevo = pd.DataFrame(nuevos_pronosticos)

    df_existente = cargar_pronosticos()
    if df_existente.empty:
        st.error(
            "⚠️ Error de seguridad: no se cargaron los pronósticos existentes. "
            "No se guardó nada para evitar borrar datos."
        )
        st.stop()
    usuario = st.session_state.usuario
    ids_partidos = df_nuevo["partido_id"].tolist()

    df_existente = df_existente[
        ~(
            (df_existente["usuario"] == usuario) &
            (df_existente["partido_id"].isin(ids_partidos))
        )
    ]

    df_final = pd.concat(
        [df_existente, df_nuevo],
        ignore_index=True
    )

    escribir_sheet("pronosticos", df_final)


# -----------------------------
# Cálculo de puntos
# -----------------------------

def tipo_resultado(goles_local, goles_visitante):
    if goles_local > goles_visitante:
        return "local"
    elif goles_local < goles_visitante:
        return "visitante"
    else:
        return "empate"


def calcular_puntos(pronostico, resultado):
    puntos = 0
    detalle = []

    p_local = int(pronostico["goles_local"])
    p_visitante = int(pronostico["goles_visitante"])
    r_local = int(resultado["goles_local"])
    r_visitante = int(resultado["goles_visitante"])

    # Ganador o empate correcto
    if tipo_resultado(p_local, p_visitante) == tipo_resultado(r_local, r_visitante):
        puntos += 3
        detalle.append("Ganador/empate correcto (+3)")

    # Marcador exacto
    if p_local == r_local and p_visitante == r_visitante:
        puntos += 4
        detalle.append("Marcador exacto (+4)")

    # Goles de uno de los equipos
    if p_local == r_local or p_visitante == r_visitante:
        puntos += 1
        detalle.append("Goles de un equipo (+1)")

    # Diferencia de gol
    if (p_local - p_visitante) == (r_local - r_visitante):
        puntos += 1
        detalle.append("Diferencia correcta (+1)")

    return puntos, " | ".join(detalle)


def calcular_tabla_puntos():
    pronosticos = cargar_pronosticos()
    resultados = cargar_resultados()

    if pronosticos.empty or resultados.empty:
        return pd.DataFrame()

    filas = []

    for _, pronostico in pronosticos.iterrows():

        resultado_partido = resultados[
            resultados["partido_id"] == pronostico["partido_id"]
        ]

        if resultado_partido.empty:
            continue

        resultado = resultado_partido.iloc[0]

        puntos, detalle = calcular_puntos(pronostico, resultado)

        filas.append({
            "usuario": pronostico["usuario"],
            "partido_id": pronostico["partido_id"],
            "partido": f"{pronostico['equipo_local']} vs {pronostico['equipo_visitante']}",
            "pronostico": f"{pronostico['goles_local']}-{pronostico['goles_visitante']}",
            "resultado": f"{resultado['goles_local']}-{resultado['goles_visitante']}",
            "puntos": puntos,
            "detalle": detalle
        })

    return pd.DataFrame(filas)
def obtener_posicion_usuario(usuario):
    tabla_puntos = calcular_tabla_puntos()

    if tabla_puntos.empty:
        return None, 0

    ranking = (
        tabla_puntos
        .groupby("usuario", as_index=False)["puntos"]
        .sum()
        .sort_values("puntos", ascending=False)
    )

    ranking.insert(0, "puesto", range(1, len(ranking) + 1))

    fila_usuario = ranking[ranking["usuario"] == usuario]

    if fila_usuario.empty:
        return None, 0

    puesto = int(fila_usuario.iloc[0]["puesto"])
    puntos = int(fila_usuario.iloc[0]["puntos"])

    return puesto, puntos

def obtener_posicion_usuario(usuario):
    tabla_puntos = calcular_tabla_puntos()

    if tabla_puntos.empty:
        return None, 0

    ranking = (
        tabla_puntos
        .groupby("usuario", as_index=False)["puntos"]
        .sum()
        .sort_values("puntos", ascending=False)
    )

    ranking.insert(0, "puesto", range(1, len(ranking) + 1))

    fila_usuario = ranking[ranking["usuario"] == usuario]

    if fila_usuario.empty:
        return None, 0

    puesto = int(fila_usuario.iloc[0]["puesto"])
    puntos = int(fila_usuario.iloc[0]["puntos"])

    return puesto, puntos


# -----------------------------
# Datos iniciales
# -----------------------------

jugadores = cargar_jugadores()

partidos = cargar_partidos()

if "jornada" not in partidos.columns:
    st.warning(
        "⚠️ No se pudieron cargar los partidos. Refresca la página."
    )
    st.stop()

if "logueado" not in st.session_state:
    st.session_state.logueado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""

if "es_admin" not in st.session_state:
    st.session_state.es_admin = False

st.title("⚽ La Pollada")

ADMIN_USER = "admin"
ADMIN_PIN = "7392"

# -----------------------------
# Login
# -----------------------------

if not st.session_state.logueado:

    st.subheader("Ingreso de participantes")

    nombre = st.selectbox(
        "Selecciona tu nombre",
        [ADMIN_USER] + jugadores["nombre"].tolist()
    )

    pin = st.text_input(
        "PIN",
        type="password"
    )

    if st.button("Entrar"):

        if nombre == ADMIN_USER:
            if pin == ADMIN_PIN:
                st.session_state.logueado = True
                st.session_state.usuario = ADMIN_USER
                st.session_state.es_admin = True
                st.rerun()
            else:
                st.error("PIN de administrador incorrecto.")

        else:
            jugador = jugadores[jugadores["nombre"] == nombre].iloc[0]

            if str(jugador["pin"]) == pin:
                st.session_state.logueado = True
                st.session_state.usuario = nombre
                st.session_state.es_admin = False
                st.rerun()
            else:
                st.error("PIN incorrecto. Intenta de nuevo.")

# -----------------------------
# App principal
# -----------------------------

if st.session_state.logueado:

    st.success(f"Bienvenido/a, {st.session_state.usuario} ⚽")
    if st.button("Cerrar sesión"):
        st.session_state.logueado = False
        st.session_state.usuario = ""
        st.session_state.es_admin = False
        st.rerun()
    if st.session_state.es_admin:

        st.write("## 🛠️ Panel de administrador")
        st.write("## 📋 Estado de pronósticos")

        jornada_admin = st.selectbox(
            "Selecciona fecha para revisar",
            [
                "Primera fecha de grupos",
                "Segunda fecha de grupos",
                "Tercera fecha de grupos",
                "16avos de final",
                "Octavos de final",
                "Cuartos de final",
                "Semifinal",
                "Tercer puesto",
                "Final"
            ],
            key="admin_jornada"
        )

        jugadores_df = cargar_jugadores()
        partidos_df = cargar_partidos()
        pronosticos_df = cargar_pronosticos()

        partidos_jornada = partidos_df[
            partidos_df["jornada"] == jornada_admin
        ]

        ids_jornada = partidos_jornada["id"].tolist()
        total_partidos = len(ids_jornada)

        filas_estado = []

        for _, jugador in jugadores_df.iterrows():

            usuario = jugador["nombre"]

            pronosticos_usuario = pronosticos_df[
                (pronosticos_df["usuario"] == usuario) &
                (pronosticos_df["partido_id"].isin(ids_jornada))
            ]

            cantidad = len(pronosticos_usuario)

            if cantidad == total_partidos:
                estado = "✅ Completo"
            elif cantidad == 0:
                estado = "❌ Sin llenar"
            else:
                estado = "⚠️ Incompleto"

            filas_estado.append({
                "Usuario": usuario,
                "Llenados": cantidad,
                "Total": total_partidos,
                "Estado": estado
            })

        estado_df = pd.DataFrame(filas_estado)

        st.dataframe(
            estado_df,
            use_container_width=True,
            hide_index=True
        )
        st.write("### Resultados oficiales")

        resultados = cargar_resultados()

        if resultados.empty:
            st.info("Todavía no hay resultados cargados.")
        else:
            st.dataframe(
                resultados,
                use_container_width=True,
                hide_index=True
            )
        st.write("### Registrar resultado")

        opciones = {
            f"{row['id']} - {row['equipo_local']} vs {row['equipo_visitante']}": row["id"]
            for _, row in partidos_df.iterrows()
        }

        seleccion = st.selectbox(
            "Partido",
            list(opciones.keys()),
            key="admin_partido"
        )

        partido_id = opciones[seleccion]

        partido = partidos_df[
            partidos_df["id"] == partido_id
        ].iloc[0]

        st.write(
            f"**{partido['equipo_local']} vs {partido['equipo_visitante']}**"
        )

        goles_local = st.number_input(
            "Goles local",
            min_value=0,
            max_value=20,
            key="admin_gl"
        )

        goles_visitante = st.number_input(
            "Goles visitante",
            min_value=0,
            max_value=20,
            key="admin_gv"
        )

        if st.button("Guardar resultado oficial"):

            guardar_resultado(
                partido_id,
                goles_local,
                goles_visitante
            )

            st.success("Resultado guardado ✅")
            st.rerun()
        
            st.write("## 📊 Previa del partido")

        opciones_previa = {
            f"{row['equipo_local']} vs {row['equipo_visitante']}": row["id"]
            for _, row in partidos_df.iterrows()
        }

        partido_previa = st.selectbox(
            "Selecciona partido",
            list(opciones_previa.keys()),
            key="admin_previa"
        )

        partido_id_previa = opciones_previa[partido_previa]

        pronosticos_previa = pronosticos_df[
            pronosticos_df["partido_id"] == partido_id_previa
        ]

        st.write(
            f"Pronósticos recibidos: {len(pronosticos_previa)}"
        )
        if not pronosticos_previa.empty:

            local_gana = len(
            pronosticos_previa[
            pronosticos_previa["goles_local"] >
            pronosticos_previa["goles_visitante"]
        ]
    )

        empate = len(
        pronosticos_previa[
            pronosticos_previa["goles_local"] ==
            pronosticos_previa["goles_visitante"]
        ]
    )

        visitante_gana = len(
        pronosticos_previa[
            pronosticos_previa["goles_local"] <
            pronosticos_previa["goles_visitante"]
        ]
    )

        total = len(pronosticos_previa)

        st.write("### 📈 Tendencia de la comunidad")

        st.write(
        f"🏠 Local: {local_gana/total:.0%}"
    )

        st.write(
        f"🤝 Empate: {empate/total:.0%}"
    )

        st.write(
        f"✈️ Visitante: {visitante_gana/total:.0%}"
    )
        st.write("### 🎯 Marcador más votado")

        marcadores = (
        pronosticos_previa["goles_local"].astype(str)
        + "-"
        + pronosticos_previa["goles_visitante"].astype(str)
    )

        conteo = marcadores.value_counts()

        marcador_top = conteo.index[0]
        votos_top = conteo.iloc[0]

        st.success(
        f"{marcador_top} ({votos_top} votos)"
    )
        st.write("### ⚽ Promedio de goles esperado")

        promedio_local = pronosticos_previa["goles_local"].mean()
        promedio_visitante = pronosticos_previa["goles_visitante"].mean()

        st.write(
        f"🏠 Local: {promedio_local:.2f}"
    )

        st.write(
        f"✈️ Visitante: {promedio_visitante:.2f}"
    )
        st.write("### 🤠 Rebeldes")

        if empate >= local_gana and empate >= visitante_gana:
            tendencia = "Empate"

            rebeldes = pronosticos_previa[
            pronosticos_previa["goles_local"] !=
            pronosticos_previa["goles_visitante"]
        ]

        elif local_gana >= visitante_gana:
            tendencia = "Local"

            rebeldes = pronosticos_previa[
            pronosticos_previa["goles_local"] <
            pronosticos_previa["goles_visitante"]
        ]

        else:
            tendencia = "Visitante"

            rebeldes = pronosticos_previa[
            pronosticos_previa["goles_local"] >
            pronosticos_previa["goles_visitante"]
        ]

        st.write(f"📈 Tendencia mayoritaria: **{tendencia}**")
        if rebeldes.empty:
            st.success("Nadie va contra la corriente 😄")
        else:

          for _, fila in rebeldes.head(10).iterrows():

            st.write(
                f"• {fila['usuario']} → "
                f"{fila['goles_local']}-{fila['goles_visitante']}"
            )

        st.write("## 🏆 Post-partido")

        opciones_post = {
            f"{row['id']} - {row['equipo_local']} vs {row['equipo_visitante']}": row["id"]
            for _, row in partidos_df.iterrows()
        }

        partido_post = st.selectbox(
            "Selecciona partido para resumen post-partido",
            list(opciones_post.keys()),
            key="admin_post_partido"
        )

        partido_id_post = opciones_post[partido_post]

        resultado_post = resultados[
            resultados["partido_id"] == partido_id_post
        ]

        if resultado_post.empty:
            st.info("Todavía no hay resultado oficial para este partido.")
        else:
            resultado_fila = resultado_post.iloc[0]

            pronosticos_post = pronosticos_df[
                pronosticos_df["partido_id"] == partido_id_post
            ]

            if pronosticos_post.empty:
                st.info("No hay pronósticos para este partido.")
            else:
                r_local = int(resultado_fila["goles_local"])
                r_visitante = int(resultado_fila["goles_visitante"])

                st.write(f"Resultado real: **{r_local}-{r_visitante}**")

                exactos = pronosticos_post[
                    (pronosticos_post["goles_local"].astype(int) == r_local) &
                    (pronosticos_post["goles_visitante"].astype(int) == r_visitante)
                ]

                st.write("### 🎯 Acertaron marcador exacto")

                if exactos.empty:
                    st.info("Nadie acertó el marcador exacto.")
                else:
                    st.success(", ".join(exactos["usuario"].tolist()))
                st.write("## 🧩 Editar cruces de eliminatorias")

        partidos_eliminatoria = partidos_df[
            partidos_df["jornada"].isin([
                "16avos de final",
                "Octavos de final",
                "Cuartos de final",
                "Semifinal",
                "Tercer puesto",
                "Final"
            ])
        ]

        if partidos_eliminatoria.empty:
            st.info("Todavía no hay partidos de eliminatoria cargados.")
        else:
            opciones_elim = {
                f"{row['id']} - {row['jornada']} - {row['equipo_local']} vs {row['equipo_visitante']}": row["id"]
                for _, row in partidos_eliminatoria.iterrows()
            }

            partido_editar = st.selectbox(
                "Selecciona partido a editar",
                list(opciones_elim.keys()),
                key="admin_editar_elim"
            )

            partido_id_editar = opciones_elim[partido_editar]

            fila_partido = partidos_df[
                partidos_df["id"] == partido_id_editar
            ].iloc[0]

            nuevo_local = st.text_input(
                "Equipo local",
                value=fila_partido["equipo_local"],
                key="editar_local"
            )

            nuevo_visitante = st.text_input(
                "Equipo visitante",
                value=fila_partido["equipo_visitante"],
                key="editar_visitante"
            )

            if st.button("Guardar cruce"):

                partidos_df.loc[
                    partidos_df["id"] == partido_id_editar,
                    "equipo_local"
                ] = nuevo_local

                partidos_df.loc[
                    partidos_df["id"] == partido_id_editar,
                    "equipo_visitante"
                ] = nuevo_visitante

                escribir_sheet("partidos", partidos_df)

                st.success("Cruce actualizado ✅")
                st.rerun()
        st.stop()
        
        

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pronósticos",
        "Clasificación",
        "Detalle de puntos",
        "⭐ Predicciones",
        "Reglas",
        
])

    with tab1:

        puesto, puntos_usuario = obtener_posicion_usuario(st.session_state.usuario)

        col1, col2, col3 = st.columns(3)

        with col1:
            if puesto is None:
                st.metric("Mi posición 🏆", "Sin puntos")
            else:
                st.metric("Mi posición 🏆", f"#{puesto}")

        with col2:
            st.metric("Puntos Mundial 🏆", puntos_usuario)

        with col3:
            st.metric("🐶 Oli Puntos ", 0)
        pronosticos_guardados = cargar_pronosticos()
        resultados = cargar_resultados()
        pronosticos_usuario = pronosticos_guardados[
            pronosticos_guardados["usuario"] == st.session_state.usuario
        ]

        pronosticos = []

        fecha_seleccionada = st.selectbox(
            "📅 Selecciona la fecha",
            [
                "Primera fecha de grupos",
                "Segunda fecha de grupos",
                "Tercera fecha de grupos",
                "16avos de final",
                "Octavos de final",
                "Cuartos de final",
                "Semifinal",
                "Tercer puesto",
                "Final"
            ],
            key="fecha_usuario"
        )
        partidos_jornada_ids = partidos[
            partidos["jornada"] == fecha_seleccionada
        ]["id"].tolist()

        cantidad_guardados = len(
            pronosticos_usuario[
                pronosticos_usuario["partido_id"].isin(partidos_jornada_ids)
            ]
        )

        total_jornada = len(partidos_jornada_ids)

        st.header(fecha_seleccionada)

        st.info(
            f"📋 Pronósticos guardados: {cantidad_guardados}/{total_jornada}"
        )
        if cantidad_guardados == total_jornada:
            st.success("✅ Jornada completa")
        else:
            st.warning(
                f"⚠️ Te faltan {total_jornada - cantidad_guardados} partidos"
            )
        st.header(fecha_seleccionada)

        st.warning(
            "⚠️ Los cambios NO se guardan automáticamente. "
            "Al terminar, baja hasta el final y pulsa 'Guardar pronósticos'."
        )

        if "jornada" not in partidos.columns:
            st.warning("⚠️ No se pudieron cargar los partidos. Refresca la página.")
            st.stop()

        partidos = partidos[
            partidos["jornada"] == fecha_seleccionada
        ]

        for _, partido in partidos.iterrows():

            fecha_partido = pd.to_datetime(partido["fecha"]).tz_convert(None)

            partido_cerrado = datetime.now() >= fecha_partido

            fila = pronosticos_usuario[
                pronosticos_usuario["partido_id"] == partido["id"]
            ]

            if not fila.empty:
                valor_local = int(fila.iloc[0]["goles_local"])
                valor_visitante = int(fila.iloc[0]["goles_visitante"])
            else:
                valor_local = 0
                valor_visitante = 0

            resultado_partido = resultados[
                resultados["partido_id"] == partido["id"]
            ]

            partido_bloqueado = not resultado_partido.empty

            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])

            with col1:
                st.write(f"**{partido['equipo_local']}**")

            with col2:
                goles_local = st.number_input(
                    " ",
                    min_value=0,
                    max_value=20,
                    value=valor_local,
                    key=f"local_{partido['id']}",
                    disabled=partido_cerrado or partido_bloqueado
                )

            with col3:
                st.write("vs")

            with col4:
                goles_visitante = st.number_input(
                    " ",
                    min_value=0,
                    max_value=20,
                    value=valor_visitante,
                    key=f"visitante_{partido['id']}",
                    disabled=partido_cerrado or partido_bloqueado
                )

            with col5:
                st.write(f"**{partido['equipo_visitante']}**")

            if partido_bloqueado:

                if fila.empty:
                    st.info(
                        "ℹ️ No registraste pronóstico antes del cierre."
                    )
                else:
                    st.write(
                        f"Tu pronóstico: {valor_local}-{valor_visitante}"
                    )

                st.warning(
                    "🔒 Partido bloqueado: ya tiene resultado oficial."
                )

            if partido_cerrado and not partido_bloqueado:
                st.warning(
                    "⏰ Pronóstico cerrado: el partido ya comenzó."
                )

            pronosticos.append({
                "usuario": st.session_state.usuario,
                "partido_id": partido["id"],
                "equipo_local": partido["equipo_local"],
                "equipo_visitante": partido["equipo_visitante"],
                "goles_local": goles_local,
                "goles_visitante": goles_visitante
            })

            st.divider()
        if st.button("Guardar pronósticos"):
            guardar_pronosticos(pronosticos)
            st.success("Pronósticos guardados correctamente ✅")
        st.write("## 📋 Resumen de mis pronósticos")

        resumen = ""

        for p in pronosticos:
            resumen += (
            f"{p['equipo_local']} {p['goles_local']}-"
            f"{p['goles_visitante']} {p['equipo_visitante']}\n"
    )

        st.text_area(
            "Copia o toma captura de este resumen",
            resumen,
            height=300
)   
    with tab2:

        st.write("## Clasificación general")

        tabla_puntos = calcular_tabla_puntos()

        if tabla_puntos.empty:
            st.info("Todavía no hay puntos calculados.")
        else:
            ranking = (
                tabla_puntos
                .groupby("usuario", as_index=False)["puntos"]
                .sum()
                .sort_values("puntos", ascending=False)
            )

            ranking.insert(0, "puesto", range(1, len(ranking) + 1))

            medallas = []

            for i in range(len(ranking)):
                if i == 0:
                    medallas.append("🥇")
                elif i == 1:
                    medallas.append("🥈")
                elif i == 2:
                    medallas.append("🥉")
                else:
                    medallas.append("")

            ranking.insert(1, "medalla", medallas)

            st.write("### 🏆 Podio")

            top3 = ranking.head(3)

            cols = st.columns(3)

            for i, (_, fila) in enumerate(top3.iterrows()):
                with cols[i]:
                    if fila["puesto"] == 1:
                        st.markdown(f"## 🥇 {fila['usuario']}")
                    elif fila["puesto"] == 2:
                        st.markdown(f"## 🥈 {fila['usuario']}")
                    elif fila["puesto"] == 3:
                        st.markdown(f"## 🥉 {fila['usuario']}")

                    st.metric("Puntos", int(fila["puntos"]))

            st.write("### Tabla completa")

            st.dataframe(
                ranking,
                use_container_width=True,
                hide_index=True
            )
    with tab3:

        st.write("## Detalle de puntos por partido")

        tabla_puntos = calcular_tabla_puntos()

        if tabla_puntos.empty:
            st.info("Todavía no hay detalle disponible.")
        else:
            st.dataframe(
                tabla_puntos,
                use_container_width=True,
                hide_index=True
            )
    with tab4:

        st.write("## ⭐ Predicciones especiales")

        predicciones_guardadas = cargar_predicciones_especiales()

        fila = predicciones_guardadas[
            predicciones_guardadas["usuario"] ==
            st.session_state.usuario
    ]

        campeon_default = ""
        subcampeon_default = ""
        tercero_default = ""
        goleador_default = ""
        jugador_default = ""
        arquero_default = ""

        if not fila.empty:

            campeon_default = fila.iloc[0]["campeon"]
            subcampeon_default = fila.iloc[0]["subcampeon"]
            tercero_default = fila.iloc[0]["tercer_lugar"]
            goleador_default = fila.iloc[0]["maximo_goleador"]
            jugador_default = fila.iloc[0]["mejor_jugador"]
            arquero_default = fila.iloc[0]["mejor_arquero"]

            campeon = st.text_input(
            "🏆 Campeón",
            value=campeon_default
    )

            subcampeon = st.text_input(
            "🥈 Subcampeón",
            value=subcampeon_default
    )

            tercer_lugar = st.text_input(
            "🥉 Tercer lugar",
            value=tercero_default
    )

            maximo_goleador = st.text_input(
            "⚽ Máximo goleador",
            value=goleador_default
    )

            mejor_jugador = st.text_input(
            "⭐ Mejor jugador",
            value=jugador_default
    )

            mejor_arquero = st.text_input(
            "🧤 Mejor arquero",
            value=arquero_default
    )

        if st.button("Guardar predicciones especiales"):

         guardar_predicciones_especiales(
            st.session_state.usuario,
            {
                "usuario": st.session_state.usuario,
                "campeon": campeon,
                "subcampeon": subcampeon,
                "tercer_lugar": tercer_lugar,
                "maximo_goleador": maximo_goleador,
                "mejor_jugador": mejor_jugador,
                "mejor_arquero": mejor_arquero
            }
        )

        st.success("Predicciones guardadas ✅")
    with tab5:

        st.write("## 📜 Reglas de La Pollada")

        st.write("### 1. Puntuación por partido")

        st.table({
            "Concepto": [
                "Ganador o empate correcto",
                "Marcador exacto",
                "Goles de uno de los equipos",
                "Diferencia de gol correcta"
            ],
            "Puntos": [
                3,
                4,
                1,
                1
            ]
        })

        st.info(
            "Los puntos son acumulativos. "
            "Si una persona acierta el marcador exacto, también suma los puntos "
            "por ganador, goles de un equipo y diferencia de gol."
        )

        st.write("### 2. Fase eliminatoria")

        st.write(
            """
            En octavos, cuartos, semifinal y final, el marcador corresponde al resultado
            al finalizar los 90 minutos reglamentarios, incluyendo reposición.

            Además, cada participante deberá escoger el equipo clasificado.
            """
        )

        st.table({
            "Concepto": [
                "Ganador o empate correcto en 90 min",
                "Marcador exacto en 90 min",
                "Goles de uno de los equipos",
                "Diferencia de gol correcta",
                "Equipo clasificado correcto"
            ],
            "Puntos": [
                3,
                4,
                1,
                1,
                3
            ]
        })

        st.write("### 3. Predicciones de largo plazo")

        st.table({
            "Predicción": [
                "Campeón",
                "Subcampeón",
                "Tercer lugar",
                "Máximo goleador",
                "Mejor jugador",
                "Mejor arquero"
            ],
            "Puntos": [
                18,
                15,
                12,
                12,
                12,
                12
            ]
        })

        st.write("### 4. Reglas operativas")

        st.write(
            """
            - Valor de inscripción: **50.000 COP**.
            - Premios: **70% primer lugar, 20% segundo lugar, 10% tercer lugar**.
            - Si hay empate, el premio se divide entre los participantes empatados.
            - Las inscripciones cierran 10 minutos antes del primer partido del Mundial.
            - Cada jornada cierra 10 minutos antes del primer partido de esa jornada.
            - Después del cierre no se pueden modificar pronósticos.
            """
        )

        st.write("### 5. 🐶 Oli Puntos ⭐")

        st.write(
            """
            Los Oli Puntos son puntos especiales para premios sorpresa,
            rifas, Melositas, Cocosette u otros regalos.

            No afectan la clasificación oficial de La Pollada.
            """
        )
        #Migracion a Google Sheets
