# src/summarizer/summary_templates.py
class SummaryTemplates:
    def __init__(self):
        self.templates = {
            'brief': """
                Provide a brief summary of the chat history in 2-3 sentences.
                Focus on the main topics discussed and key decisions made.
                Keep it concise and informative.
            """,
            
            'detailed': """
                Provide a detailed summary of the chat history, including:
                1. Main topics discussed
                2. Key decisions and agreements
                3. Action items and next steps
                4. Important questions raised
                Use bullet points for clarity when appropriate.
            """,
            
            'key_points': """
                Extract the most important points from the conversation.
                Return them as a bullet-point list.
                Focus on actionable items, decisions, and key information.
            """,
            
            'topic': """
                Analyze the conversation and identify the main topics discussed.
                Group related messages together and provide a summary for each topic.
                Include timestamps and participant information where relevant.
            """
        }
        
    def get_template(self, template_type: str) -> str:
        """Get template by type"""
        return self.templates.get(template_type, self.templates['brief'])
