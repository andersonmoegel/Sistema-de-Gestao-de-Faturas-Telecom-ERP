import os
import re
import sqlite3
import pdfplumber
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
from datetime import datetime

# ================= CONFIGURAÇÃO E IDENTIDADE =================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB = os.path.join(DIRETORIO_ATUAL, "telecom_shared.db")

try:
    USUARIO_MAQUINA = os.getlogin().upper()
except:
    USUARIO_MAQUINA = "SISTEMA"

AZUL_PRINCIPAL = "#00579D"
BG_APP = "#F2F4F7"
CARD_BG = "#FFFFFF"
VERDE_SOFT = "#27AE60"
VERMELHO_SOFT = "#E74C3C"

EMPRESAS = ["1001","1004","1007","1009","1013","1014","1016","1019","1027"]
OPERADORAS = sorted(["ALGAR","ATHENA","BITWAVE","BRDIGITAL","CLARO","EMBRATEL","FENIX","GNET","GWM","INVISTA","MUNDIVOX","NORTE TELECOM","OI","ORANGE","SIM FIBRA","TIM","UNIFIQUE","VIVO"])

MAPA_CNPJ = {
    "12345678000123": "1001", "12345678000234": "1001", "12345678000345": "1001",
    "98765432000198": "1027", "87654321000765": "1007", "76543210000432": "1016",
    "65432100000210": "1019", "54321000000109": "1009", "43210000000987": "1014",
    "32100000000123": "1013", "21000000000198": "1004"
}

def conectar():
    conn = sqlite3.connect(CAMINHO_DB, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS faturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT, operadora TEXT, mes_ano TEXT, valor REAL, 
        vencimento TEXT, data_envio TEXT, ritm TEXT, nf_servico TEXT, usuario TEXT)""")
    conn.commit()
    return conn

def formatar_moeda_br(valor):
    """Converte float para string formato R$ 1.250,00"""
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

# ================= MOTOR DE EXTRAÇÃO REFINADO =================
def extrair_inteligente(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo).upper()
    dados = {"valor": None, "vencimento": None, "empresa": None, "operadora": None}

    for op in OPERADORAS:
        if op in nome_arquivo:
            dados["operadora"] = op
            break

    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += (page.extract_text() or "") + "\n"
            
            texto_u = texto_completo.upper()

            # --- 1. MELHORIA NA CAPTURA DE CNPJ (VALIDAÇÃO DIRETA) ---
            # Buscamos padrões de 14 dígitos com ou sem formatação no texto
            # Isso evita que a "massa numérica" junte números de faturas com CNPJ
            todos_cnpjs_texto = re.findall(r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{14}', texto_u)
            
            for cnpj_encontrado in todos_cnpjs_texto:
                cnpj_limpo = re.sub(r'\D', '', cnpj_encontrado) # Remove . / -
                if cnpj_limpo in MAPA_CNPJ:
                    dados["empresa"] = str(MAPA_CNPJ[cnpj_limpo])
                    break

            # --- 2. MELHORIA NA CAPTURA DE VALOR (FILTRAGEM DE RUÍDO) ---
            # Criamos uma lista de âncoras mais específicas para evitar valores parciais
            ancoras_valor = [
                r"TOTAL A PAGAR", r"VALOR TOTAL DA FATURA", r"VALOR TOTAL", 
                r"TOTAL DESTA FATURA", r"VALOR LÍQUIDO", r"VALOR DO PAGAMENTO"
            ]
            
            # Removemos quebras de linha para busca linear mas mantemos espaços
            texto_para_valor = " ".join(texto_u.split())
            candidatos_valor = []

            for ancora in ancoras_valor:
                # Busca o valor num raio de 40 caracteres após a âncora
                # A regex garante que pegamos um formato financeiro (0,00)
                match = re.search(ancora + r".{0,40}?(?:\s|R\$)\s*(\d{1,3}(?:\.\d{3})*,\d{2})", texto_para_valor)
                if match:
                    val_raw = match.group(1)
                    val_limpo = val_raw.replace(".", "").replace(",", ".")
                    try:
                        val_float = float(val_limpo)
                        # Geralmente o valor total é um dos maiores da primeira página
                        if val_float > 0.1:
                            candidatos_valor.append(val_float)
                    except: continue
            
            if candidatos_valor:
                # Priorizamos o valor encontrado pelas âncoras (geralmente o último das âncoras é o sumário)
                dados["valor"] = candidatos_valor[0]
            else:
                # Backup: se não achou âncora, pega o maior valor monetário do topo do PDF
                todos_valores = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", texto_u[:2000]) # Primeiros 2000 chars
                if todos_valores:
                    nums = [float(v.replace(".", "").replace(",", ".")) for v in todos_valores]
                    dados["valor"] = max(nums) if nums else None

            # --- 3. CAPTURA DE VENCIMENTO (MANTIDA - VOCÊ INFORMOU QUE ESTÁ ÓTIMA) ---
            datas_str = re.findall(r'(\d{2}/\d{2}/\d{4})', texto_u)
            datas_venc = []
            for d in datas_str:
                try:
                    dt = datetime.strptime(d, "%d/%m/%Y")
                    if 2024 <= dt.year <= 2030: datas_venc.append(dt)
                except: continue
            if datas_venc:
                dados["vencimento"] = max(datas_venc)

    except Exception as e:
        print(f"Erro na extração: {e}")
    
    return dados

# ================= INTERFACE DE CONSULTA COM VALOR PT-BR =================
def configurar_estilo_tabela():
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Treeview",
        background="#FFFFFF",
        foreground="#333333",
        rowheight=35,
        fieldbackground="#FFFFFF",
        borderwidth=0,
        font=("Segoe UI", 10)
    )

    style.configure("Treeview.Heading",
        background="#F8F9FA",
        foreground="#00579D",
        relief="flat",
        font=("Segoe UI", 11, "bold")
    )

    style.map("Treeview",
        background=[('selected', "#00579D")],
        foreground=[('selected', 'white')]
    )


class JanelaConsulta(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Painel de Controle Telecom")
        self.geometry("1300x800")
        self.configure(fg_color=BG_APP)
        self.grab_set()

        # Configura o estilo global da Treeview
        configurar_estilo_tabela()

        # --- HEADER ---
        header = ctk.CTkFrame(self, fg_color=AZUL_PRINCIPAL, height=60, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="PAINEL DE CONSULTA E FILTROS", text_color="white", font=("Arial", 20, "bold")).pack(pady=15)

        # --- CARD DE FILTROS ---
        self.filtro_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=15)
        self.filtro_card.pack(padx=20, pady=15, fill="x")

        f_container = ctk.CTkFrame(self.filtro_card, fg_color="transparent")
        f_container.pack(pady=15, padx=20)

        filtros_labels = ["Empresa:", "Operadora:", "Mês:", "Ano:", "RITM:"]
        for i, text in enumerate(filtros_labels):
            ctk.CTkLabel(f_container, text=text, font=("Arial", 11, "bold")).grid(row=0, column=i*2, padx=5, sticky="e")

        self.f_emp = ctk.CTkComboBox(f_container, values=["TODAS"] + EMPRESAS, width=90)
        self.f_emp.set("TODAS"); self.f_emp.grid(row=0, column=1, padx=5)

        self.f_ope = ctk.CTkComboBox(f_container, values=["TODAS"] + OPERADORAS, width=130)
        self.f_ope.set("TODAS"); self.f_ope.grid(row=0, column=3, padx=5)

        self.f_mes = ctk.CTkComboBox(f_container, values=["TODOS"] + [f"{i:02d}" for i in range(1, 13)], width=80)
        self.f_mes.set("TODOS"); self.f_mes.grid(row=0, column=5, padx=5)

        self.f_ano = ctk.CTkComboBox(f_container, values=["TODOS", "2023", "2024", "2025", "2026"], width=90)
        self.f_ano.set("TODOS"); self.f_ano.grid(row=0, column=7, padx=5)

        self.f_ritm = ctk.CTkEntry(f_container, placeholder_text="Busca...", width=100)
        self.f_ritm.grid(row=0, column=9, padx=5)

        btn_search = ctk.CTkButton(f_container, text="🔍 FILTRAR", fg_color=AZUL_PRINCIPAL, width=100, font=("bold", 12), command=self.carregar_dados)
        btn_search.grid(row=0, column=10, padx=15)

        # --- CARD DA TABELA ---
        self.table_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=15, border_width=1, border_color="#E0E0E0")
        self.table_card.pack(padx=20, pady=(0, 20), fill="both", expand=True)

        self.lbl_total = ctk.CTkLabel(self.table_card, text="Total: R$ 0,00", font=("Arial", 18, "bold"), text_color=AZUL_PRINCIPAL)
        self.lbl_total.pack(pady=10)

        # Scrollbar
        self.scroll = ctk.CTkScrollbar(self.table_card, orientation="vertical")
        self.scroll.pack(side="right", fill="y", padx=(0, 5), pady=5)

        self.tree = ttk.Treeview(
            self.table_card, 
            columns=("ID","Empresa","Operadora","Ref","Valor","Venc","Envio","NF","RITM","Status","User"), 
            show="headings",
            yscrollcommand=self.scroll.set
        )
        self.scroll.configure(command=self.tree.yview)

        # CONFIGURAÇÃO DE TAGS DIRETAMENTE NA TREEVIEW (CORREÇÃO DO ERRO)
        self.tree.tag_configure('vencido', foreground="#E74C3C") 
        self.tree.tag_configure('noprazo', foreground="#27AE60")
        
        cols = {"ID": 45, "Empresa": 75, "Operadora": 130, "Ref": 80, "Valor": 115, "Venc": 110, "Envio": 110, "NF": 45, "RITM": 110, "Status": 100, "User": 105}
        for c, w in cols.items():
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor="center")
        
        self.tree.pack(expand=True, fill="both", padx=15, pady=10)
        self.tree.bind("<Double-1>", self.abrir_edicao)
        
        ctk.CTkLabel(self.table_card, text="💡 Clique duplo para editar ou excluir.", font=("Arial", 11, "italic"), text_color="gray").pack(pady=5)
        self.carregar_dados()

    def carregar_dados(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = conectar()
        query = "SELECT * FROM faturas WHERE 1=1"
        params = []
        
        if self.f_emp.get() != "TODAS":
            query += " AND empresa = ?"; params.append(self.f_emp.get())
        if self.f_ope.get() != "TODAS":
            query += " AND operadora = ?"; params.append(self.f_ope.get())
        if self.f_mes.get() != "TODOS":
            query += " AND strftime('%m', mes_ano) = ?"; params.append(self.f_mes.get())
        if self.f_ano.get() != "TODOS":
            query += " AND strftime('%Y', mes_ano) = ?"; params.append(self.f_ano.get())
        if self.f_ritm.get():
            query += " AND ritm LIKE ?"; params.append(f"%{self.f_ritm.get()}%")

        df = pd.read_sql_query(query, conn, params=params)
        total = 0
        hoje = datetime.now().date()
        
        for _, r in df.iterrows():
            total += r['valor']
            v_br = formatar_moeda_br(r['valor'])
            
            try:
                data_venc_dt = datetime.strptime(r['vencimento'], "%Y-%m-%d").date()
                dt_venc_exibicao = data_venc_dt.strftime("%d/%m/%Y")
                dt_envio_exibicao = datetime.strptime(r['data_envio'], "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                data_venc_dt = hoje
                dt_venc_exibicao, dt_envio_exibicao = r['vencimento'], r['data_envio']

            if data_venc_dt < hoje:
                status_txt = "● VENCIDO"
                tag = 'vencido'
            else:
                status_txt = "● NO PRAZO"
                tag = 'noprazo'
            
            self.tree.insert("", "end", values=(
                r['id'], r['empresa'], r['operadora'], r['mes_ano'][:7], 
                v_br, dt_venc_exibicao, dt_envio_exibicao, r['nf_servico'], r['ritm'], status_txt, r['usuario']
            ), tags=(tag,))
        
        self.lbl_total.configure(text=f"VALOR TOTAL DOS REGISTROS: R$ {formatar_moeda_br(total)}")
        conn.close()

    def abrir_edicao(self, event):
        item = self.tree.selection()
        if item:
            JanelaEdicao(self, self.tree.item(item)['values'])

# ================= JANELA DE EDIÇÃO (PADRÃO WEG) =================
class JanelaEdicao(ctk.CTkToplevel):
    def __init__(self, parent, valores):
        super().__init__(parent)
        self.parent = parent
        self.registro_id = valores[0]
        self.title("Gerenciar Registro")
        self.geometry("500x700")
        self.configure(fg_color=BG_APP)
        self.grab_set() # Foca apenas nesta janela

        # Header
        header = ctk.CTkFrame(self, fg_color=AZUL_PRINCIPAL, height=60, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"EDIÇÃO DO REGISTRO #{self.registro_id}", text_color="white", font=("Arial", 16, "bold")).pack(pady=15)

        # Card Principal
        self.card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=15)
        self.card.pack(padx=20, pady=20, fill="both", expand=True)

        # --- Campos de Edição ---
        self.cb_emp = self.add_field("Empresa:", EMPRESAS, valores[1], is_cb=True)
        self.cb_ope = self.add_field("Operadora:", OPERADORAS, valores[2], is_cb=True)
        
        # Tratamento do valor (remove formatação BR para editar o número puro)
        valor_limpo = str(valores[4]).replace(".", "").replace(",", ".")
        self.en_val = self.add_field("Valor (R$):", None, valor_limpo)
        
        self.dt_venc = self.add_field("Vencimento:", None, valores[5], is_date=True)
        self.en_ritm = self.add_field("RITM:", None, valores[8])
        
        self.check_nf = ctk.CTkCheckBox(self.card, text="Possui NF de Serviço", font=("Arial", 12))
        if valores[7] == "Sim": self.check_nf.select()
        self.check_nf.pack(pady=15)

        # --- Botões de Ação ---
        btn_save = ctk.CTkButton(self.card, text="💾 SALVAR ALTERAÇÕES", fg_color=VERDE_SOFT, 
                                 height=45, font=("bold", 14), command=self.atualizar)
        btn_save.pack(pady=(20, 10), padx=40, fill="x")

        btn_del = ctk.CTkButton(self.card, text="🗑️ EXCLUIR REGISTRO", fg_color=VERMELHO_SOFT, 
                                height=45, font=("bold", 14), command=self.deletar)
        btn_del.pack(pady=0, padx=40, fill="x")

    def add_field(self, label, options, default, is_cb=False, is_date=False):
        ctk.CTkLabel(self.card, text=label, font=("Arial", 12, "bold")).pack(pady=(10, 0))
        if is_cb:
            widget = ctk.CTkComboBox(self.card, values=options, width=300)
            widget.set(default)
        elif is_date:
            widget = DateEntry(self.card, locale='pt_BR', width=28)
            # Tenta converter do formato PT-BR que veio da tabela
            try:
                data_dt = datetime.strptime(default, "%d/%m/%Y")
                widget.set_date(data_dt)
            except:
                pass 
        else:
            widget = ctk.CTkEntry(self.card, width=300)
            widget.insert(0, default)
        
        widget.pack(pady=(0, 5))
        return widget

    def atualizar(self):
        try:
            val = float(self.en_val.get())
            conn = conectar()
            conn.execute("""UPDATE faturas SET empresa=?, operadora=?, valor=?, vencimento=?, ritm=?, nf_servico=? 
                         WHERE id=?""", (self.cb_emp.get(), self.cb_ope.get(), val, 
                         self.dt_venc.get_date().strftime("%Y-%m-%d"), self.en_ritm.get(),
                         "Sim" if self.check_nf.get() else "Não", self.registro_id))
            conn.commit(); conn.close()
            messagebox.showinfo("Sucesso", "Dados atualizados!")
            self.parent.carregar_dados(); self.destroy()
        except Exception as e: messagebox.showerror("Erro", f"Falha ao atualizar: {e}")

    def deletar(self):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este registro permanentemente?"):
            conn = conectar(); conn.execute("DELETE FROM faturas WHERE id=?", (self.registro_id,))
            conn.commit(); conn.close()
            self.parent.carregar_dados(); self.destroy()()


# ================= APP PRINCIPAL =================
class AppTelecom(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Gestão de Faturas Telecom | Logado como: {USUARIO_MAQUINA}")
        self.geometry("900x820")
        self.configure(fg_color=BG_APP)

        # --- HEADER ---
        header = ctk.CTkFrame(self, fg_color=AZUL_PRINCIPAL, height=80, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="GESTÃO DE FATURAS TELECOM", font=("Arial", 24, "bold"), text_color="white").pack(pady=20)

        # --- CONTAINER PRINCIPAL (CARD) ---
        self.card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=20)
        self.card.pack(padx=40, pady=30, fill="both", expand=True)
        
        self.setup_widgets()

    def setup_widgets(self):
        # Configuração de colunas para o formulário
        self.card.columnconfigure((0, 1), weight=1, pad=20)

        # --- SEÇÃO 1: IMPORTAÇÃO ---
        section_title_1 = ctk.CTkLabel(self.card, text="1. ENTRADA DE DADOS", font=("Arial", 16, "bold"), text_color=AZUL_PRINCIPAL)
        section_title_1.grid(row=0, column=0, columnspan=2, pady=(25, 15), padx=30, sticky="w")

        self.btn_import = ctk.CTkButton(self.card, text="📂 SELECIONAR ARQUIVO PDF (AUTO-SCAN)", 
                                        font=("Arial", 14, "bold"), fg_color=AZUL_PRINCIPAL, hover_color="#00457C",
                                        height=50, command=self.importar)
        self.btn_import.grid(row=1, column=0, columnspan=2, pady=(0, 20), padx=30, sticky="ew")

        separator = ctk.CTkFrame(self.card, height=2, fg_color="#E0E0E0")
        separator.grid(row=2, column=0, columnspan=2, sticky="ew", padx=30, pady=10)

        # --- SEÇÃO 2: DETALHES DA FATURA ---
        section_title_2 = ctk.CTkLabel(self.card, text="2. CONFERÊNCIA DOS CAMPOS", font=("Arial", 16, "bold"), text_color=AZUL_PRINCIPAL)
        section_title_2.grid(row=3, column=0, columnspan=2, pady=(15, 10), padx=30, sticky="w")

        # Rótulo e Campo: Empresa
        self.lbl_emp = ctk.CTkLabel(self.card, text="Empresa (Código):", font=("Arial", 12, "bold"))
        self.lbl_emp.grid(row=4, column=0, padx=30, sticky="w")
        self.cb_emp = ctk.CTkComboBox(self.card, values=EMPRESAS, width=320, height=35)
        self.cb_emp.grid(row=5, column=0, padx=30, pady=(0, 15), sticky="w")

        # Rótulo e Campo: Operadora
        self.lbl_ope = ctk.CTkLabel(self.card, text="Operadora de Telecom:", font=("Arial", 12, "bold"))
        self.lbl_ope.grid(row=4, column=1, padx=30, sticky="w")
        self.cb_ope = ctk.CTkComboBox(self.card, values=OPERADORAS, width=320, height=35)
        self.cb_ope.grid(row=5, column=1, padx=30, pady=(0, 15), sticky="w")

        # Rótulo e Campo: Valor
        self.lbl_val = ctk.CTkLabel(self.card, text="Valor da Fatura (R$):", font=("Arial", 12, "bold"))
        self.lbl_val.grid(row=6, column=0, padx=30, sticky="w")
        self.en_val = ctk.CTkEntry(self.card, width=320, height=35, placeholder_text="Ex: 1250.00")
        self.en_val.grid(row=7, column=0, padx=30, pady=(0, 15), sticky="w")

        # Rótulo e Campo: Vencimento
        self.lbl_venc = ctk.CTkLabel(self.card, text="Data de Vencimento:", font=("Arial", 12, "bold"))
        self.lbl_venc.grid(row=6, column=1, padx=30, sticky="w")
        self.dt_venc = DateEntry(self.card, locale='pt_BR', width=25, background=AZUL_PRINCIPAL, foreground='white', borderwidth=2)
        self.dt_venc.grid(row=7, column=1, padx=30, pady=(0, 15), sticky="ew")

        # Rótulo e Campo: RITM
        self.lbl_ritm = ctk.CTkLabel(self.card, text="Número da RITM / Chamado:", font=("Arial", 12, "bold"))
        self.lbl_ritm.grid(row=8, column=0, padx=30, sticky="w")
        self.en_ritm = ctk.CTkEntry(self.card, width=320, height=35, placeholder_text="Digite o número da RITM")
        self.en_ritm.grid(row=9, column=0, padx=30, pady=(0, 15), sticky="w")

        # Checkbox NF
        self.check_nf = ctk.CTkCheckBox(self.card, text="Fatura possui Nota Fiscal de Serviço?", 
                                        font=("Arial", 12), fg_color=AZUL_PRINCIPAL)
        self.check_nf.grid(row=9, column=1, padx=30, sticky="w")

        # --- BOTÃO SALVAR ---
        self.btn_save = ctk.CTkButton(self.card, text="💾 FINALIZAR E SALVAR REGISTRO", 
                                      font=("Arial", 16, "bold"), fg_color=VERDE_SOFT, hover_color="#1E8449",
                                      height=60, command=self.salvar)
        self.btn_save.grid(row=10, column=0, columnspan=2, pady=40, padx=30, sticky="ew")

        # --- RODAPÉ COM ATALHO ---
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", pady=20)
        
        self.btn_history = ctk.CTkButton(footer_frame, text="📊 ACESSAR HISTÓRICO DE LANÇAMENTOS", 
                                         font=("Arial", 13), fg_color="#34495E", hover_color="#2C3E50",
                                         width=350, height=40, command=lambda: JanelaConsulta(self))
        self.btn_history.pack()

    def importar(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            dados = extrair_inteligente(path)
            if dados["empresa"]: self.cb_emp.set(dados["empresa"])
            if dados["operadora"]: self.cb_ope.set(dados["operadora"])
            if dados["valor"]: 
                self.en_val.delete(0, "end")
                self.en_val.insert(0, f"{dados['valor']:.2f}")
            if dados["vencimento"]: self.dt_venc.set_date(dados["vencimento"])
            messagebox.showinfo("Scanner", "PDF Processado!")

    def salvar(self):
        try:
            val = float(self.en_val.get().replace(",", "."))
            conn = conectar()
            conn.execute("INSERT INTO faturas (empresa, operadora, mes_ano, valor, vencimento, data_envio, ritm, nf_servico, usuario) VALUES (?,?,?,?,?,?,?,?,?)",
                         (self.cb_emp.get(), self.cb_ope.get(), self.dt_venc.get_date().strftime("%Y-%m-01"), val, self.dt_venc.get_date().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"), self.en_ritm.get(), "Não", USUARIO_MAQUINA))
            conn.commit(); conn.close(); messagebox.showinfo("Sucesso", "Salvo!")
        except: messagebox.showerror("Erro", "Falha nos dados")

if __name__ == "__main__":
    conectar()
    AppTelecom().mainloop()