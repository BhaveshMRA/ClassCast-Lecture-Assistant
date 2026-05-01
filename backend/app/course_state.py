"""
Simple in-memory state to hold uploaded course materials (syllabus/notes).
Used for Long-Context RAG injection.
"""

class CourseState:
    def __init__(self):
        self.syllabus_text: str | None = None
        
    def set_syllabus(self, text: str):
        self.syllabus_text = text
        
    def get_syllabus(self) -> str | None:
        return self.syllabus_text
        
    def clear(self):
        self.syllabus_text = None

# Singleton
course_state = CourseState()
