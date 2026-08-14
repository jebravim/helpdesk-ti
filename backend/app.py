from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import query
from config import SECRET_KEY
import secrets

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ============================================================
# INÍCIO
# ============================================================

@app.route("/")
def inicio():
    """
    Página inicial para o usuário.
    O usuário comum não entra mais no dashboard.
    """
    return redirect(url_for("novo_chamado"))


# ============================================================
# ABERTURA DE CHAMADO PELO USUÁRIO
# ============================================================

@app.route("/chamados/novo", methods=["GET", "POST"])
def novo_chamado():

    # --------------------------------------------------------
    # POST - registrar chamado
    # --------------------------------------------------------

    if request.method == "POST":

        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        nome = request.form.get("nome", "").strip()
        setor = request.form.get("setor", "").strip()
        prioridade = request.form.get("prioridade", "").strip()

        # ----------------------------------------------------
        # Validação
        # ----------------------------------------------------

        if not titulo or not descricao or not nome or not setor or not prioridade:

            setores = query("""
                SELECT DISTINCT setor
                FROM usuarios
                WHERE setor IS NOT NULL
                  AND TRIM(setor) <> ''
                ORDER BY setor
            """)

            return render_template(
                "novo_chamado.html",
                setores=setores,
                erro="Preencha todos os campos."
            )

        # ----------------------------------------------------
        # Gera código único de acompanhamento
        # ----------------------------------------------------

        codigo = secrets.token_urlsafe(12)

        # ----------------------------------------------------
        # Cria o chamado
        # ----------------------------------------------------

        chamado = query(
            """
            INSERT INTO chamados (
                titulo,
                descricao,
                prioridade,
                status,
                solicitante_nome,
                solicitante_setor,
                data_abertura,
                data_fechamento,
                codigo_acompanhamento
            )
            VALUES (
                %s,
                %s,
                %s,
                'aberto',
                %s,
                %s,
                NOW(),
                NULL,
                %s
            )
            RETURNING id, codigo_acompanhamento
            """,
            (
                titulo,
                descricao,
                prioridade,
                nome,
                setor,
                codigo
            ),
        )

        # ----------------------------------------------------
        # Recupera os dados criados
        # ----------------------------------------------------

        chamado_id = chamado[0]["id"]
        codigo_acompanhamento = chamado[0]["codigo_acompanhamento"]

        # ----------------------------------------------------
        # Vai para a tela de confirmação
        # ----------------------------------------------------

        return render_template(
            "chamado_criado.html",
            chamado_id=chamado_id,
            codigo_acompanhamento=codigo_acompanhamento,
            nome=nome,
            setor=setor,
        )

    # --------------------------------------------------------
    # GET - carregar setores
    # --------------------------------------------------------

    setores = query(
        """
        SELECT DISTINCT setor
        FROM usuarios
        WHERE setor IS NOT NULL
          AND TRIM(setor) <> ''
        ORDER BY setor
        """
    )

    return render_template(
        "novo_chamado.html",
        setores=setores
    )


# ============================================================
# ACOMPANHAMENTO DE CHAMADOS
# ============================================================

@app.route("/meus-chamados", methods=["GET", "POST"])
def meus_chamados():

    codigo = ""

    if request.method == "POST":
        codigo = request.form.get(
            "codigo_acompanhamento",
            ""
        ).strip()

    else:
        codigo = request.args.get(
            "codigo",
            ""
        ).strip()

    chamados = []

    if codigo:

        chamados = query(
            """
            SELECT
                id,
                titulo,
                descricao,
                prioridade,
                status,
                solicitante_nome,
                solicitante_setor,
                data_abertura,
                data_fechamento
            FROM chamados
            WHERE codigo_acompanhamento = %s
            ORDER BY data_abertura DESC
            """,
            (codigo,),
        )

    return render_template(
        "meus_chamados.html",
        chamados=chamados,
        codigo=codigo,
    )


# ============================================================
# DASHBOARD DOS TÉCNICOS
# ============================================================

@app.route("/tecnico")
def dashboard_tecnico():

    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")

    sql = """
        SELECT
            c.id,
            c.titulo,
            c.prioridade,
            c.status,
            c.data_abertura,
            c.data_fechamento,
            c.solicitante_nome,
            c.solicitante_setor,
            u2.nome AS tecnico,
            e.tipo AS equipamento_tipo,
            e.modelo AS equipamento_modelo

        FROM chamados c

        LEFT JOIN usuarios u2
            ON c.tecnico_id = u2.id

        LEFT JOIN equipamentos e
            ON c.equipamento_id = e.id

        WHERE 1=1
    """

    params = []

    if status_filtro:
        sql += " AND c.status = %s"
        params.append(status_filtro)

    if prioridade_filtro:
        sql += " AND c.prioridade = %s"
        params.append(prioridade_filtro)

    sql += " ORDER BY c.data_abertura DESC"

    chamados = query(sql, params)

    # --------------------------------------------------------
    # Contadores
    # --------------------------------------------------------

    contadores = query("""
        SELECT status, COUNT(*) AS total
        FROM chamados
        GROUP BY status
    """)

    contadores_dict = {
        c["status"]: c["total"]
        for c in contadores
    }

    # --------------------------------------------------------
    # Tempo médio de resolução
    # --------------------------------------------------------

    tempo_medio = query("""
        SELECT ROUND(
            AVG(
                EXTRACT(
                    EPOCH FROM (
                        data_fechamento - data_abertura
                    )
                ) / 3600
            )::numeric,
            1
        ) AS media_horas

        FROM chamados

        WHERE status = 'fechado'
          AND data_fechamento IS NOT NULL
    """)

    media_horas = (
        tempo_medio[0]["media_horas"]
        if tempo_medio
        else None
    )

    return render_template(
        "index.html",
        chamados=chamados,
        abertos=contadores_dict.get("aberto", 0),
        em_andamento=contadores_dict.get("em_andamento", 0),
        fechados=contadores_dict.get("fechado", 0),
        media_horas=media_horas,
        status_filtro=status_filtro,
        prioridade_filtro=prioridade_filtro,
    )


# ============================================================
# DETALHES DO CHAMADO
# ============================================================

@app.route("/chamados/<int:chamado_id>")
def detalhes_chamado(chamado_id):

    chamado = query(
        """
        SELECT
            c.*,
            u2.nome AS tecnico,
            e.tipo AS equipamento_tipo,
            e.modelo AS equipamento_modelo

        FROM chamados c

        LEFT JOIN usuarios u2
            ON c.tecnico_id = u2.id

        LEFT JOIN equipamentos e
            ON c.equipamento_id = e.id

        WHERE c.id = %s
        """,
        (chamado_id,),
    )

    historico = query(
        """
        SELECT
            h.comentario,
            h.data,
            u.nome AS autor

        FROM historico_chamados h

        LEFT JOIN usuarios u
            ON h.autor_id = u.id

        WHERE h.chamado_id = %s

        ORDER BY h.data ASC
        """,
        (chamado_id,),
    )

    tecnicos = query(
        """
        SELECT id, nome
        FROM usuarios
        WHERE tipo IN ('tecnico', 'admin')
        ORDER BY nome
        """
    )

    return render_template(
        "detalhes_chamado.html",
        chamado=chamado[0] if chamado else None,
        historico=historico,
        tecnicos=tecnicos,
    )


# ============================================================
# ATUALIZAÇÃO DO CHAMADO PELO TÉCNICO
# ============================================================

@app.route(
    "/chamados/<int:chamado_id>/atualizar",
    methods=["POST"]
)
def atualizar_chamado(chamado_id):

    novo_status = request.form.get("status", "").strip()
    tecnico_id = request.form.get("tecnico_id") or None
    tecnico_nome = request.form.get("tecnico_nome", "").strip()
    comentario = request.form.get("comentario", "").strip()

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    if not novo_status:
        return "Status não informado.", 400

    # Para assumir ou atualizar o chamado,
    # o técnico precisa informar o próprio nome.
    if novo_status in ("em_andamento", "fechado") and not tecnico_nome:
        return "Informe o nome do técnico.", 400

    # --------------------------------------------------------
    # Chamado fechado
    # --------------------------------------------------------

    if novo_status == "fechado":

        query(
            """
            UPDATE chamados
            SET
                status = %s,
                tecnico_id = %s,
                tecnico_nome = %s,
                data_fechamento = NOW()
            WHERE id = %s
            """,
            (
                novo_status,
                tecnico_id,
                tecnico_nome,
                chamado_id
            ),
            fetch=False
        )

    # --------------------------------------------------------
    # Chamado em andamento
    # --------------------------------------------------------

    else:

        query(
            """
            UPDATE chamados
            SET
                status = %s,
                tecnico_id = %s,
                tecnico_nome = %s,
                data_fechamento = NULL
            WHERE id = %s
            """,
            (
                novo_status,
                tecnico_id,
                tecnico_nome,
                chamado_id
            ),
            fetch=False
        )

    # --------------------------------------------------------
    # Histórico
    # --------------------------------------------------------

    if comentario:

        query(
            """
            INSERT INTO historico_chamados (
                chamado_id,
                comentario,
                autor_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                chamado_id,
                comentario,
                tecnico_id
            ),
            fetch=False
        )

    return redirect(
        url_for(
            "detalhes_chamado",
            chamado_id=chamado_id
        )
    )


# ============================================================
# API - LISTAR CHAMADOS
# ============================================================

@app.route("/api/chamados", methods=["GET"])
def api_listar_chamados():

    chamados = query(
        """
        SELECT *
        FROM chamados
        ORDER BY data_abertura DESC
        """
    )

    return jsonify(chamados)


# ============================================================
# API - CRIAR CHAMADO
# ============================================================

@app.route("/api/chamados", methods=["POST"])
def api_criar_chamado():

    dados = request.get_json()

    codigo = secrets.token_urlsafe(12)

    novo = query(
        """
        INSERT INTO chamados (
            titulo,
            descricao,
            prioridade,
            status,
            solicitante_nome,
            solicitante_setor,
            data_abertura,
            codigo_acompanhamento
        )

        VALUES (
            %s,
            %s,
            %s,
            'aberto',
            %s,
            %s,
            NOW(),
            %s
        )

        RETURNING id, codigo_acompanhamento
        """,
        (
            dados.get("titulo"),
            dados.get("descricao"),
            dados.get("prioridade", "media"),
            dados.get("solicitante_nome"),
            dados.get("solicitante_setor"),
            codigo,
        ),
    )

    return jsonify(novo), 201


# ============================================================
# API - ATUALIZAR CHAMADO
# ============================================================

@app.route(
    "/api/chamados/<int:chamado_id>",
    methods=["PUT"]
)
def api_atualizar_chamado(chamado_id):

    dados = request.get_json()

    novo_status = dados.get("status")

    if novo_status == "fechado":

        query(
            """
            UPDATE chamados
            SET
                status = %s,
                data_fechamento = NOW()
            WHERE id = %s
            """,
            (
                novo_status,
                chamado_id
            ),
            fetch=False,
        )

    else:

        query(
            """
            UPDATE chamados
            SET
                status = %s,
                data_fechamento = NULL
            WHERE id = %s
            """,
            (
                novo_status,
                chamado_id
            ),
            fetch=False,
        )

    return jsonify({
        "mensagem": "Chamado atualizado com sucesso"
    })


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=False,
        port=5000
    )