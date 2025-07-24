from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data, DataFrame
import requests
import pandas as pd
import re
import json

class BigDataCorpCompanyInfo(Component):
    display_name = "BigDataCorp Company"
    description = "Consults the BigDataCorp API for company registration data using CNPJ."
    icon = "mdi-domain"
    name = "BigDataCorpCompanyInfo"

    inputs = [
        SecretStrInput(
            name="access_token",
            display_name="Access Token",
            info="Your BigDataCorp Access Token.",
            required=True
        ),
        SecretStrInput(
            name="token_id",
            display_name="Token ID",
            info="Your BigDataCorp Token ID.",
            required=True
        ),
        StrInput(
            name="cnpj",
            display_name="CNPJ",
            info="CNPJ da empresa (apenas números). Ex: 28352868000170",
            tool_mode=True,
            required=True
        ),
        StrInput(
            name="view",
            display_name="View",
            info="The view your user has access to (required by API).",
            advanced=True,
            required=False
        ),
        StrInput(
            name="datasets",
            display_name="Datasets",
            info="Dataset(s) to include in the request (e.g., 'registration_data').",
            required=False,
            value="registration_data"
        )
    ]

    outputs = [
        Output(name="company_data", display_name="Company Data", method="get_company_data")
    ]

    def clean_cnpj(self, cnpj):
        """Remove caracteres especiais do CNPJ e valida formato"""
        # Remove tudo exceto números
        cnpj_clean = re.sub(r'[^\d]', '', str(cnpj))
        
        # Verifica se tem 14 dígitos
        if len(cnpj_clean) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        
        return cnpj_clean

    def get_company_data(self) -> DataFrame:
        print("🚀 INICIANDO CONSULTA DE EMPRESA")
        print(f"CNPJ recebido: {self.cnpj}")
        print(f"Access Token: {self.access_token[:10]}..." if self.access_token else "NÃO FORNECIDO")
        print(f"Token ID: {self.token_id[:10]}..." if self.token_id else "NÃO FORNECIDO")
        print(f"View: {self.view}")
        print(f"Datasets: {self.datasets}")
        
        url = "https://plataforma.bigdatacorp.com.br/empresas"
        
        # Limpa e valida o CNPJ
        try:
            cnpj_clean = self.clean_cnpj(self.cnpj)
            print(f"✅ CNPJ limpo: {cnpj_clean}")
        except ValueError as e:
            print(f"❌ Erro na validação do CNPJ: {e}")
            return DataFrame(pd.DataFrame({"error": [str(e)]}))
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "AccessToken": self.access_token,
            "TokenId": self.token_id
        }
        
        # FORMATO CORRETO: q com doc{CNPJ}
        payload = {
            "q": f"doc{{{cnpj_clean}}}",
            "Datasets": self.datasets
        }
        
        # Adiciona view se fornecido
        if self.view:
            payload["view"] = self.view

        # Logs detalhados para debug
        print("=== BIGDATACORP COMPANY DEBUG ===")
        print(f"URL: {url}")
        print(f"CNPJ Original: {self.cnpj}")
        print(f"CNPJ Limpo: {cnpj_clean}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("=" * 40)

        try:
            print("📡 Enviando requisição...")
            response = requests.post(url, headers=headers, json=payload)
            
            # Log da resposta
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            print("=" * 40)
            
            response.raise_for_status()
            result = response.json()

            if isinstance(result, dict):
                df = pd.DataFrame([result])
                print("✅ Sucesso! Retornando dados da empresa")
                return DataFrame(df)
            elif isinstance(result, list):
                df = pd.DataFrame(result)
                print("✅ Sucesso! Retornando lista de empresas")
                return DataFrame(df)
            else:
                print("⚠️ Formato de resposta inesperado")
                return DataFrame(pd.DataFrame({"error": ["Unexpected API response format."]}))

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            self.status = f"Request error: {e}"
            return DataFrame(pd.DataFrame({"error": [str(e)]}))
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            self.status = f"Unexpected error: {e}"
            return DataFrame(pd.DataFrame({"error": [str(e)]})) 