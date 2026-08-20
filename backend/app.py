from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from database import query
from config import SECRET_KEY
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ============================================================
# LOGIN (TÉCNICO/ADMIN)
# ============================================================
# NOVO: proteção por sessão para a área do técnico.
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("tecnico_login", proximo=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("tecnico_login", proximo=request.path))
        if session.get("usuario_tipo") != "admin":
            return "Acesso restrito a administradores.", 403
        return f(*args, **kwargs)
    return decorated


@app.route("/tecnico/login", methods=["GET", "POST"])
def tecnico_login():

    erro = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()

        usuario = query(
            """
            SELECT id, nome, tipo, senha_hash
            FROM usuarios
            WHERE email = %s
              AND tipo IN ('tecnico', 'admin')
            """,
            (email,),
        )

        senha_ok = (
            usuario
            and usuario[0]["senha_hash"]
            and check_password_hash(usuario[0]["senha_hash"], senha)
        )

        if not senha_ok:
            erro = "E-mail ou senha inválidos."
        else:
            session["usuario_id"] = usuario[0]["id"]
            session["usuario_nome"] = usuario[0]["nome"]
            session["usuario_tipo"] = usuario[0]["tipo"]

            proximo = request.args.get("proximo") or url_for("dashboard_tecnico")
            return redirect(proximo)

    return render_template("tecnico_login.html", erro=erro)


@app.route("/tecnico/logout")
def tecnico_logout():
    session.clear()
    return redirect(url_for("tecnico_login"))


# ============================================================
# CRIAR SENHA (PRIMEIRO ACESSO DO TÉCNICO)
# ============================================================
# NOVO: só permite definir senha se o usuário já existe (cadastrado
# pelo admin direto no banco, com email/nome/tipo) e ainda não tem
# senha_hash definido. Evita que alguém sobrescreva senha alheia.
# ============================================================

@app.route("/tecnico/criar-senha", methods=["GET", "POST"])
def criar_senha_tecnico():

    erro = None
    sucesso = False

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        confirmar = request.form.get("confirmar", "").strip()

        if not email or not senha or not confirmar:
            erro = "Preencha todos os campos."
        elif senha != confirmar:
            erro = "As senhas não coincidem."
        elif len(senha) < 6:
            erro = "A senha precisa ter pelo menos 6 caracteres."
        else:
            usuario = query(
                """
                SELECT id, senha_hash
                FROM usuarios
                WHERE email = %s
                  AND tipo IN ('tecnico', 'admin')
                """,
                (email,),
            )

            if not usuario:
                erro = "E-mail não encontrado. Fale com o administrador do sistema."
            elif usuario[0]["senha_hash"]:
                erro = "Este usuário já tem uma senha definida. Faça login normalmente."
            else:
                query(
                    "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                    (generate_password_hash(senha), usuario[0]["id"]),
                    fetch=False,
                )
                sucesso = True

    return render_template(
        "criar_senha_tecnico.html",
        erro=erro,
        sucesso=sucesso,
    )


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

            # ATUALIZADO: setores agora vêm da tabela dedicada "setores"
            setores = query("SELECT id, nome FROM setores ORDER BY nome")

            return render_template(
                "novo_chamado.html",
                setores=setores,
                erro="Preencha todos os campos."
            )

        # ----------------------------------------------------
        # Cria o chamado (código é preenchido em seguida,
        # pois depende do id gerado pelo banco)
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
                data_fechamento
            )
            VALUES (
                %s,
                %s,
                %s,
                'aberto',
                %s,
                %s,
                NOW(),
                NULL
            )
            RETURNING id
            """,
            (
                titulo,
                descricao,
                prioridade,
                nome,
                setor,
            ),
        )

        chamado_id = chamado[0]["id"]

        # ----------------------------------------------------
        # NOVO: código com padrão CH-<ano>-<id com 5 dígitos>
        # em vez de string aleatória (ex: CH-2026-00001)
        # ----------------------------------------------------

        codigo_acompanhamento = f"CH-{datetime.now().year}-{chamado_id:05d}"

        query(
            "UPDATE chamados SET codigo_acompanhamento = %s WHERE id = %s",
            (codigo_acompanhamento, chamado_id),
            fetch=False,
        )

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

    # ATUALIZADO: setores agora vêm da tabela dedicada "setores"
    setores = query("SELECT id, nome FROM setores ORDER BY nome")

    return render_template(
        "novo_chamado.html",
        setores=setores
    )


# ============================================================
# ACOMPANHAMENTO DE CHAMADOS
# ============================================================
# ATUALIZADO: busca agora é por nome (obrigatório), com o
# código de acompanhamento como filtro opcional para desempatar
# nomes repetidos.
# ============================================================

@app.route("/meus-chamados", methods=["GET", "POST"])
def meus_chamados():

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        codigo = request.form.get("codigo_acompanhamento", "").strip()
        buscou = True
    else:
        nome = request.args.get("nome", "").strip()
        codigo = request.args.get("codigo", "").strip()
        buscou = bool(nome)

    chamados = []
    erro = None

    if buscou:

        if not nome:
            erro = "Informe o nome para buscar."

        else:

            sql = """
                SELECT
                    id,
                    titulo,
                    descricao,
                    prioridade,
                    status,
                    solicitante_nome,
                    solicitante_setor,
                    data_abertura,
                    data_fechamento,
                    codigo_acompanhamento
                FROM chamados
                WHERE solicitante_nome ILIKE %s
            """

            params = [nome]

            if codigo:
                sql += " AND codigo_acompanhamento = %s"
                params.append(codigo)

            sql += " ORDER BY data_abertura DESC"

            chamados = query(sql, params)

    return render_template(
        "meus_chamados.html",
        chamados=chamados,
        nome=nome,
        codigo=codigo,
        erro=erro,
    )


# ============================================================
# DETALHES DO CHAMADO PARA O USUÁRIO
# ============================================================

@app.route("/meus-chamados/<int:chamado_id>")
def detalhes_chamado_usuario(chamado_id):

    # Busca o chamado
    chamado = query(
        """
        SELECT
            c.id,
            c.titulo,
            c.descricao,
            c.prioridade,
            c.status,
            c.solicitante_nome,
            c.solicitante_setor,
            c.data_abertura,
            c.data_fechamento,
            c.codigo_acompanhamento,
            c.tecnico_nome
        FROM chamados c
        WHERE c.id = %s
        """,
        (chamado_id,)
    )

    if not chamado:
        return "Chamado não encontrado.", 404

    chamado = chamado[0]

    # Busca o histórico da resolução
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
        (chamado_id,)
    )

    return render_template(
        "chamado_detalhes_usuario.html",
        chamado=chamado,
        historico=historico
    )
# ============================================================
# GERENCIAR TÉCNICOS (SOMENTE ADMIN)
# ============================================================
# CRUD de usuários técnicos/admin. Só quem tem
# session["usuario_tipo"] == "admin" acessa.
# ============================================================

@app.route("/tecnico/gerenciar", methods=["GET", "POST"])
@admin_required
def gerenciar_tecnicos():

    erro = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        setor = request.form.get("setor", "").strip()
        tipo = request.form.get("tipo", "tecnico").strip()
        senha = request.form.get("senha", "").strip()

        if not nome or not email:
            erro = "Nome e e-mail são obrigatórios."
        elif tipo not in ("tecnico", "admin"):
            erro = "Tipo inválido."
        else:
            existe = query("SELECT id FROM usuarios WHERE email = %s", (email,))

            if existe:
                erro = "Já existe um usuário com esse e-mail."
            else:
                senha_hash = generate_password_hash(senha) if senha else None

                query(
                    """
                    INSERT INTO usuarios (nome, email, setor, tipo, senha_hash)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nome, email, setor or None, tipo, senha_hash),
                    fetch=False,
                )

    tecnicos = query(
        """
        SELECT
            id,
            nome,
            email,
            setor,
            tipo,
            (senha_hash IS NOT NULL) AS tem_senha
        FROM usuarios
        WHERE tipo IN ('tecnico', 'admin')
        ORDER BY nome
        """
    )

    return render_template(
        "tecnicos.html",
        tecnicos=tecnicos,
        erro=erro,
    )


@app.route("/tecnico/gerenciar/<int:usuario_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_tecnico(usuario_id):

    erro = None

    resultado = query(
        "SELECT id, nome, email, setor, tipo FROM usuarios WHERE id = %s",
        (usuario_id,),
    )

    if not resultado:
        return "Técnico não encontrado.", 404

    tecnico = resultado[0]

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        setor = request.form.get("setor", "").strip()
        tipo = request.form.get("tipo", "tecnico").strip()
        nova_senha = request.form.get("senha", "").strip()

        # mantém os valores digitados na tela caso dê erro
        tecnico = {
            "id": usuario_id,
            "nome": nome,
            "email": email,
            "setor": setor,
            "tipo": tipo,
        }

        if not nome or not email:
            erro = "Nome e e-mail são obrigatórios."
        elif tipo not in ("tecnico", "admin"):
            erro = "Tipo inválido."
        else:
            duplicado = query(
                "SELECT id FROM usuarios WHERE email = %s AND id != %s",
                (email, usuario_id),
            )

            if duplicado:
                erro = "Já existe outro usuário com esse e-mail."
            else:
                if nova_senha:
                    query(
                        """
                        UPDATE usuarios
                        SET nome = %s, email = %s, setor = %s, tipo = %s, senha_hash = %s
                        WHERE id = %s
                        """,
                        (nome, email, setor or None, tipo, generate_password_hash(nova_senha), usuario_id),
                        fetch=False,
                    )
                else:
                    query(
                        """
                        UPDATE usuarios
                        SET nome = %s, email = %s, setor = %s, tipo = %s
                        WHERE id = %s
                        """,
                        (nome, email, setor or None, tipo, usuario_id),
                        fetch=False,
                    )

                return redirect(url_for("gerenciar_tecnicos"))

    return render_template(
        "editar_tecnico.html",
        tecnico=tecnico,
        erro=erro,
    )


@app.route("/tecnico/gerenciar/<int:usuario_id>/excluir", methods=["POST"])
@admin_required
def excluir_tecnico(usuario_id):

    # Evita que o admin logado se auto-exclua sem querer
    if usuario_id == session.get("usuario_id"):
        return "Você não pode excluir a própria conta enquanto está logado.", 400

    query("DELETE FROM usuarios WHERE id = %s", (usuario_id,), fetch=False)

    return redirect(url_for("gerenciar_tecnicos"))


# ============================================================
# GERENCIAR SETORES (ÁREA DO TÉCNICO)
# ============================================================
# NOVO: permite ao técnico logado cadastrar novos setores,
# usados no dropdown da tela de abertura de chamado.
# ============================================================

@app.route("/tecnico/setores", methods=["GET", "POST"])
@login_required
def gerenciar_setores():

    erro = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()

        if not nome:
            erro = "Informe o nome do setor."
        else:
            existe = query("SELECT id FROM setores WHERE nome ILIKE %s", (nome,))

            if existe:
                erro = "Esse setor já existe."
            else:
                query(
                    "INSERT INTO setores (nome) VALUES (%s)",
                    (nome,),
                    fetch=False,
                )

    setores = query("SELECT id, nome FROM setores ORDER BY nome")

    return render_template(
        "setores.html",
        setores=setores,
        erro=erro,
    )


# ============================================================
# DASHBOARD DOS TÉCNICOS
# ============================================================

@app.route("/tecnico")
@login_required
def dashboard_tecnico():

    status_filtro = request.args.get("status", "")
    prioridade_filtro = request.args.get("prioridade", "")
    id_filtro = request.args.get("id", "").strip()
    ordenar = request.args.get("ordenar", "recentes")

    # NOVO: whitelist de ordenação, para nunca montar ORDER BY
    # com texto vindo direto da URL (evita SQL injection).
    ORDENACOES = {
        "recentes": "c.data_abertura DESC",
        "antigos": "c.data_abertura ASC",
        "id_desc": "c.id DESC",
        "id_asc": "c.id ASC",
        "prioridade": """
            CASE c.prioridade
                WHEN 'urgente' THEN 1
                WHEN 'alta' THEN 2
                WHEN 'media' THEN 3
                WHEN 'baixa' THEN 4
                ELSE 5
            END
        """,
        "status": "c.status ASC",
    }

    if ordenar not in ORDENACOES:
        ordenar = "recentes"

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

    if id_filtro.isdigit():
        sql += " AND c.id = %s"
        params.append(int(id_filtro))

    if status_filtro:
        sql += " AND c.status = %s"
        params.append(status_filtro)

    if prioridade_filtro:
        sql += " AND c.prioridade = %s"
        params.append(prioridade_filtro)

    sql += f" ORDER BY {ORDENACOES[ordenar]}"

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
        id_filtro=id_filtro,
        ordenar=ordenar,
    )


# ============================================================
# DETALHES DO CHAMADO
# ============================================================

@app.route("/chamados/<int:chamado_id>")
@login_required
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
@login_required
def atualizar_chamado(chamado_id):

    novo_status = request.form.get("status", "").strip()
    tecnico_id = request.form.get("tecnico_id") or None
    tecnico_nome = request.form.get("tecnico_nome", "").strip()
    comentario = request.form.get("comentario", "").strip()

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    if not novo_status:
        flash("Status não informado.", "erro")
        return redirect(url_for("detalhes_chamado", chamado_id=chamado_id))

    # Para colocar em andamento ou fechar, o chamado precisa
    # ter um técnico atribuído.
    if novo_status in ("em_andamento", "fechado") and not tecnico_nome:
        flash(
            "Para colocar o chamado em andamento ou fechá-lo, "
            "é necessário atribuir um técnico responsável primeiro.",
            "erro",
        )
        return redirect(url_for("detalhes_chamado", chamado_id=chamado_id))

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

    novo = query(
        """
        INSERT INTO chamados (
            titulo,
            descricao,
            prioridade,
            status,
            solicitante_nome,
            solicitante_setor,
            data_abertura
        )

        VALUES (
            %s,
            %s,
            %s,
            'aberto',
            %s,
            %s,
            NOW()
        )

        RETURNING id
        """,
        (
            dados.get("titulo"),
            dados.get("descricao"),
            dados.get("prioridade", "media"),
            dados.get("solicitante_nome"),
            dados.get("solicitante_setor"),
        ),
    )

    chamado_id = novo[0]["id"]

    # NOVO: mesmo padrão de código usado na tela do solicitante
    codigo = f"CH-{datetime.now().year}-{chamado_id:05d}"

    query(
        "UPDATE chamados SET codigo_acompanhamento = %s WHERE id = %s",
        (codigo, chamado_id),
        fetch=False,
    )

    return jsonify({"id": chamado_id, "codigo_acompanhamento": codigo}), 201


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