import requests
import json
import mysql.connector
import random
from datetime import datetime

# Configurar as informações de conexão com o banco de dados
config = {
    'user': 'usuario',
    'password': 'senha',
    'host': 'host',
    'database': 'database'
}

conn = mysql.connector.connect(**config)
cursor = conn.cursor()

query = """
SELECT * from (SELECT fa.id as id_boleto, 
	replace(replace(replace(replace(c.telefone_celular, '(',''), ')', ''), '-', ''), ' ', '') celular,
	DAYOFWEEK(data_vencimento) as dia_semana_vencimento,
	c.razao
FROM fn_areceber fa 	
left join cliente_contrato cc on cc.id = fa.id_contrato
left join cliente c on c.id = fa.id_cliente
WHERE fa.data_vencimento BETWEEN  '2024-09-01' and CURRENT_DATE() 
and fa.filial_id not in (12, 14, 15)
and fa.status = 'A'
and cc.status = 'A'
and fa.status <> 'C' 
and coalesce(fa.id_renegociacao, 0) = 0
and COALESCE(fa.pagamento_data,'0000-00-00') = '0000-00-00' 
and fa.liberado = 'S'
and DATE_FORMAT(data_vencimento, '%Y%m') =   DATE_FORMAT(current_date(), '%Y%m')
)t 
WHERE dias_vencido = 3;
"""

# Executar a consulta SQL
cursor.execute(query)
result = cursor.fetchall()
cursor.close()
conn.close()

data = datetime.now().strftime("%d-%m-%Y")

def saudacao_atual():
    hora_atual = datetime.now().hour
    if 5 <= hora_atual < 12:
        return "Bom Dia!"
    elif 12 <= hora_atual < 18:
        return "Boa Tarde!"
    else:
        return "Boa Noite!"

def pode_enviar_mensagem():
    agora = datetime.now()
    inicio = agora.replace(hour=6, minute=30, second=0, microsecond=0)
    fim = agora.replace(hour=21, minute=0, second=0, microsecond=0)
    return inicio <= agora <= fim

if __name__ == "__main__":
    arquivo = None

    try:
        arquivo = open(f"/root/envio_cobrança_{data}.log", "a")
    except Exception as e:
        print("Erro ao abrir arquivo:", e)

    for row in result:
        if not pode_enviar_mensagem():
            print("Fora do horário permitido para envio de mensagens.")
            if arquivo is not None:
                arquivo.write("Fora do horário permitido para envio de mensagens.\n")
            break
        
        saudacao = random.choice(['Olá,', 'Oi,', saudacao_atual()])
        pergunta = random.choice(['como vai você?', 'o seu dia está ótimo?', 'a quanto tempo!!!'])
        cobranca_msg = random.choice([
            "Gostaríamos de lembrar que a fatura referente ao serviço de internet está pendente.",
            "Notamos que você tem uma fatura em aberto.",
            "Estamos entrando em contato para lembrá-lo sobre a fatura vencida.",
            "Notamos que sua fatura está pendente.",
            "Queremos apenas lembrá-lo sobre a fatura em aberto."
        ])
        
        link_msg = random.choice([
            "Entre em contato conosco pelo link: https://wa.me/xxxxxx ou pelo telefone: (81) XXXX-XXXX.",
            "Esse contato é apenas para envio; caso queira entrar em contato, fale com nosso SAC (81) xxxx-xxxx."
        ])
        
        texto_aleatorio = f'{saudacao} {pergunta} {cobranca_msg} {link_msg}'

        url_7az = f"https://api.7az.com.br/v2/integrations/omnichannel/invoices/{row[0]}/payment-data"

        headers_7az = {
            'X-API-Key': 'token',
        }
        
        try: 
            response_7az = requests.get(url_7az, headers=headers_7az)
            response_7az.raise_for_status()  
            response_json = response_7az.json()
            
            if "invoicePDFURL" not in response_json:
                print(f'Erro: URL do PDF não encontrada.{row[0]}')
                if arquivo is not None:
                    arquivo.write(f'Erro: URL do PDF não encontrada.{row[0]}\n')
                continue
            
            invoicePDFURL = response_json["invoicePDFURL"]

            url_evo = "https://evo.ve.rec.br/message/sendMedia/BBG_alertas"

            payload = json.dumps({
                "number": 'numero',  
                "options": {
                    "delay": 1200,
                    "presence": "composing"
                },
                "mediaMessage": {
                    "mediatype": "document",
                    "fileName": f"boleto_{row[0]}.pdf",
                    "caption": texto_aleatorio,
                    "media": invoicePDFURL 
                },
            })

            headers_evo = {
                'apikey': 'token',
                'Content-Type': 'application/json'
            }

            response_evo = requests.post(url_evo, headers=headers_evo, data=payload)
            response_evo.raise_for_status()  

            print(f"Mensagem enviada para {row[3]} - Telefone: {row[1]} - CPF: {row[4]} - id_contrato: {row[5]}")
            
            if arquivo is not None: 
                arquivo.write(f"Mensagem enviada para {row[3]} - Telefone: {row[1]} - CPF: {row[4]} - id_contrato: {row[5]}\n")

        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
            if arquivo is not None:
                arquivo.write(f"Erro na requisição: {e}\n")

if arquivo is not None:
    arquivo.close()