import requests
from pathlib import Path
from jams import JAMSBot

bot = JAMSBot(config_file=Path("itsm.cfg"))

class ITSM:
    def __init__(self, token: str, account: str, environment: str = 'PROD'):
        self.used_reqs = 0
        self.token = token
        self.account = account
        self.url = 'https://api.4me.com/v1/' if environment == 'PROD' else 'https://api.4me.qa/v1/'

    @property
    def header(self) -> dict:
        return {
            'Authorization': 'Bearer ' + self.token,
            'X-4me-Account': self.account
        }

    def list_organizations(self, **kwargs) -> list:
        organizations = []
        params = kwargs
        org_url = self.url + 'organizations'
        while True:
            self.used_reqs += 1
            try:
                response = requests.get(org_url, headers=self.header, params=params)
                response.raise_for_status()
            except requests.RequestException as e:
                raise bot.failed(f'Error while getting organizations data! Details: {e}')
            if not response.ok:
                raise bot.warning(f'Got {response.status_code} instead of HTTP OK while getting organizations data!'
                                  f' Details: {response.text}')
            organizations.extend(response.json())
            if 'next' in response.links:
                org_url = response.links['next']['url']
            else:
                break
        return organizations

    def update_organization(self, organization_id: int, **kwargs):
        body = kwargs
        try:
            self.used_reqs += 1
            response = requests.patch(self.url + f'organization/{organization_id}', headers=self.header, json=body)
            response.raise_for_status()
        except requests.RequestException as e:
            raise bot.failed(f'Error while updating organization: {organization_id}! Details: {e}')
        if response.status_code not in [200, 201]:
            raise bot.warning(f'Got {response.status_code} instead of HTTP 200/201 while updating organization:'
                              f' {organization_id}! Details: {response.status_code}')
        return response.json()

class OriginOperations:
    def __init__(self):
        self.origin_url = bot.get_text_var("ORIGIN", "origin_url")

    def _create_header(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_token(self) -> str:
        url = f"{self.origin_url}/api/token/create"
        user, token = bot.get_creds('ORIGIN')
        client_id, client_secret = bot.get_creds('ORIGIN2')
        body = {
            "userName": f"APP\\{user}",
            "password": token,
            "clientId": client_id,
            "clientSecret": client_secret
        }

        bot.debug("System starting to access token from Origin ...")
        response = self._post_method(url, body)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("success", False) and response_data.get("content", False):
                access_token = response_data.get("content", {}).get("accessToken", "")
                bot.debug("Token was successfully downloaded")
                return access_token
        return ""

    def get_origin_data(self) -> list:
        bot.debug("System starting to get information about the opening hours of stores from Origin ...")
        url = f"{self.origin_url}/api/v2/shop?expand=WorkHours"
        response = self._get_method(url)
        if response.status_code == 200:
            data = response.json()
            bot.debug(f"System successfully got information about {len(data)} stores opening hours from Origin")
            return data
        return []

    def _post_method(self, url: str, body: dict) -> requests.Response:
        try:
            response = requests.post(url, json=body)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as err:
            bot.warning(f"Failed HTTP request. Status code: {err.response.status_code}")
            bot.warning(f"Error message: {err.response.text}")
            bot.failed("Failed to get token from Origin.", True)

    def _get_method(self, url: str) -> requests.Response:
        try:
            response = requests.get(url, headers=self._create_header())
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as err:
            bot.warning(f"Failed HTTP request. Status code: {err.response.status_code}")
            bot.warning(f"Error message: {err.response.text}")
            bot.failed("Failed to access data from Origin.", True)

def filter_origin(data: dict) -> list:
    bot.debug("System starts filtering data from Origin ...")
    formatted_data = []
    for result in data.get("content", {}).get("results", {}):
        if 'workHours' in result:
            sorted_work_hours = sorted(result.get("workHours", []), key=lambda x: x.get("dayOfWeek", None))
            work_hours = "\n".join([f"{entry.get('hourFrom', '')[:10]}: {entry.get('hourFrom', '')[11:16]} - {entry.get('hourTo', '')[11:16]}" for entry in sorted_work_hours])
        else:
            work_hours = None
        formatted_data.append({'financialID': str(result.get("id", None)), 'godziny_otwarcia': work_hours})
    bot.debug("Filtration of data has been completed")
    return formatted_data

def filter_itsm(data: list) -> list:
    bot.debug("System starts filtering data from 4me ...")
    filtered_data = []
    for shop in data:
        id = shop.get("id", "")
        name = shop.get("name", "")
        financial_id = shop.get("financialID", "")
        custom_fields = shop.get("custom_fields", "")
        if custom_fields:
            godziny_otwarcia = next((work_hours.get("value", "") for work_hours in custom_fields if work_hours.get("id") == "godziny_otwarcia"), None)
        else:
            godziny_otwarcia = None
        filtered_data.append(dict(id=id, name=name, financialID=financial_id, godziny_otwarcia=godziny_otwarcia))
    bot.debug("Filtration of data has been completed")
    return filtered_data

def compare_loop(body: dict, origin_data: list, itsm_data: list):
    bot.debug("System starting compare data about store opening hours")
    for origin in origin_data:
        origin_financialID = origin.get("financialID", "")
        origin_godziny_otwarcia = origin.get("godziny_otwarcia", "")
        for data in itsm_data:
            itsm_shop_id = data.get("id", "")
            itsm_shop_name = data.get("name", "")
            if data.get("financialID", "") == origin_financialID:
                if data.get("godziny_otwarcia", "") != origin_godziny_otwarcia:
                    itsm_instance.update_organization(itsm_shop_id, **body)
                    bot.debug(f"{itsm_shop_name} opening hours updated.")
                else:
                    bot.debug(f"{itsm_shop_name} opening hours NOT updated.")
    bot.debug("System has finished compare the data")

if __name__ == '__main__':
    user, token = bot.get_creds('ITSM')
    origin_operations = OriginOperations()
    origin_data = filter_origin(origin_operations.get_origin_data())
    itsm_instance = ITSM(token, user, 'QA')
    itsm_data = filter_itsm(itsm_instance.list_organizations(per_page=100, source='Origin', sourceID='Origin_Shop', fields='financialID, custom_fields'))
    body = {
        "custom_fields": [
            {
                "id": "godziny_otwarcia",
                "value": "cos"
            }
        ]
    }
    compare_loop(body, origin_data, itsm_data)
       



