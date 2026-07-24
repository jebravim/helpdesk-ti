from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import query
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ============================================================
# PÁGINAS (interface web simples em HTML/Jinja2)
# ============================================================

@app.route("/")
def index():
    """Dashboard inicial com contadores e lista de chamados."""
    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")

    sql = """
        SELECT c.id, c.titulo, c.prioridade, c.status,
               c.data_abertura, c.data_fechamento,
               u1.nome AS solicitante, u2.nome AS tecnico,
               e.tipo AS equipamento_tipo, e.modelo AS equipamento_modelo
        FROM chamados c
        LEFT JOIN usuarios u1 ON c.solicitante_id = u1.id
        LEFT JOIN usuarios u2 ON c.tecnico_id = u2.id
        LEFT JOIN equipamentos e ON c.equipamento_id = e.id
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

    # Contadores para o dashboard
    contadores = query("""
        SELECT status, COUNT(*) AS total
        FROM chamados
        GROUP BY status
    """)
    contadores_dict = {c["status"]: c["total"] for c in contadores}

    # Tempo médio de resolução (em horas) dos chamados fechados
    tempo_medio = query("""
        SELECT ROUND(
            AVG(EXTRACT(EPOCH FROM (data_fechamento - data_abertura)) / 3600)::numeric, 1
        ) AS media_horas
        FROM chamados
        WHERE status = 'fechado' AND data_fechamento IS NOT NULL
    """)
    media_horas = tempo_medio[0]["media_horas"] if tempo_medio else None

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


@app.route("/chamados/novo", methods=["GET", "POST"])
def novo_chamado():
    if request.method == "POST":
        query(
            """
            INSERT INTO chamados (titulo, descricao, prioridade, solicitante_id, tecnico_id, equipamento_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request.form["titulo"],
                request.form["descricao"],
                request.form["prioridade"],
                request.form["solicitante_id"],
                request.form["tecnico_id"],
                request.form["equipamento_id"] or None,
            ),
            fetch=False,
        )
        return redirect(url_for("index"))

    usuarios = query("SELECT id, nome FROM usuarios WHERE tipo = 'solicitante'")
    usuarios = query("SELECT id, nome FROM usuarios WHERE setor = 'TI'")
    equipamentos = query("SELECT id, tipo, modelo FROM equipamentos")
    return render_template("novo_chamado.html", usuarios=usuarios, equipamentos=equipamentos)


@app.route("/chamados/<int:chamado_id>")
def detalhes_chamado(chamado_id):
    chamado = query(
        """
        SELECT c.*, u1.nome AS solicitante, u2.nome AS tecnico,
               e.tipo AS equipamento_tipo, e.modelo AS equipamento_modelo
        FROM chamados c
        LEFT JOIN usuarios u1 ON c.solicitante_id = u1.id
        LEFT JOIN usuarios u2 ON c.tecnico_id = u2.id
        LEFT JOIN equipamentos e ON c.equipamento_id = e.id
        WHERE c.id = %s
        """,
        (chamado_id,),
    )
    historico = query(
        """
        SELECT h.comentario, h.data, u.nome AS autor
        FROM historico_chamados h
        LEFT JOIN usuarios u ON h.autor_id = u.id
        WHERE h.chamado_id = %s
        ORDER BY h.data ASC
        """,
        (chamado_id,),
    )
    tecnicos = query("SELECT id, nome FROM usuarios WHERE tipo IN ('tecnico', 'admin')")
    return render_template(
        "detalhes_chamado.html",
        chamado=chamado[0] if chamado else None,
        historico=historico,
        tecnicos=tecnicos,
    )


@app.route("/chamados/<int:chamado_id>/atualizar", methods=["POST"])
def atualizar_chamado(chamado_id):
    novo_status = request.form.get("status")
    tecnico_id = request.form.get("tecnico_id")
    comentario = request.form.get("comentario")

    if novo_status == "fechado":
        query(
            """
            UPDATE chamados
            SET status = %s, tecnico_id = %s, data_fechamento = NOW()
            WHERE id = %s
            """,
            (novo_status, tecnico_id, chamado_id),
            fetch=False,
        )
    else:
        query(
            "UPDATE chamados SET status = %s, tecnico_id = %s WHERE id = %s",
            (novo_status, tecnico_id, chamado_id),
            fetch=False,
        )

    if comentario:
        query(
            "INSERT INTO historico_chamados (chamado_id, comentario, autor_id) VALUES (%s, %s, %s)",
            (chamado_id, comentario, tecnico_id),
            fetch=False,
        )

    return redirect(url_for("detalhes_chamado", chamado_id=chamado_id))


# ============================================================
# API JSON (útil para testar com Postman/Insomnia ou evoluir
# para um frontend em React no futuro)
# ============================================================

@app.route("/api/chamados", methods=["GET"])
def api_listar_chamados():
    chamados = query("SELECT * FROM chamados ORDER BY data_abertura DESC")
    return jsonify(chamados)


@app.route("/api/chamados", methods=["POST"])
def api_criar_chamado():
    dados = request.get_json()
    novo = query(
        """
        INSERT INTO chamados (titulo, descricao, prioridade, solicitante_id, tecnico_id, equipamento_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            dados.get("titulo"),
            dados.get("descricao"),
            dados.get("prioridade", "media"),
            dados.get("solicitante_id"),
            dados.get("tecnico_id"),
            dados.get("equipamento_id"),
        ),
        fetch=False,
    )
    return jsonify(novo), 201


@app.route("/api/chamados/<int:chamado_id>", methods=["PUT"])
def api_atualizar_chamado(chamado_id):
    dados = request.get_json()
    query(
        "UPDATE chamados SET status = %s WHERE id = %s",
        (dados.get("status"), chamado_id),
        fetch=False,
    )
    return jsonify({"mensagem": "Chamado atualizado com sucesso"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
