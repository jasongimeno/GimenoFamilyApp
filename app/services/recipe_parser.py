import os
import logging
from typing import List, Dict
import openai
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RecipeParser:
    def __init__(self):
        # Configure Azure OpenAI
        openai.api_type = "azure"
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
    def parse_recipe_ingredients(self, recipe_text: str) -> List[str]:
        """
        Parse recipe text and extract ingredients with quantities using GPT-3.5 Turbo
        """
        try:
            response = openai.ChatCompletion.create(
                deployment_id=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts ingredient lists from recipes."},
                    {"role": "user", "content": f"""
                        Extract only the ingredients with their quantities from the following recipe. 
                        Format each ingredient on a new line with the quantity first, followed by the ingredient name.
                        Don't include any instructions, steps, or other recipe information.
                        
                        RECIPE:
                        {recipe_text}
                    """}
                ],
                temperature=0.1,
                max_tokens=500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            ingredients_text = response.choices[0].message.content.strip()
            ingredients_list = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
            
            logger.info(f"Successfully parsed {len(ingredients_list)} ingredients from recipe")
            return ingredients_list
            
        except Exception as e:
            logger.error(f"Error parsing recipe: {str(e)}")
            raise e
    
    @staticmethod
    def get_weekly_shopping_list_name(meal_date: datetime) -> str:
        """
        Generate the shopping list name based on the meal date
        Returns name with the Monday of that week
        """
        # Find the Monday of the week
        days_since_monday = meal_date.weekday()
        monday_date = meal_date - timedelta(days=days_since_monday)
        
        # Format as mm/dd/yyyy
        monday_formatted = monday_date.strftime("%m/%d/%Y")
        
        return f"Weekly Shopping List - {monday_formatted}" 