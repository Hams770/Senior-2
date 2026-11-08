"""Skill vocabulary for extraction (FR-06). Canonical name -> spellings found in CVs.

Kept small and editable; HR can add a job's own required skills, which are matched too.
"""
SKILLS: dict[str, list[str]] = {
    # programming languages
    "python": ["python"], "java": ["java"], "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript"], "c": ["c language", "ansi c"], "c++": ["c++", "cpp"], "c#": ["c#", "csharp"],
    "go": ["golang"], "rust": ["rust"], "kotlin": ["kotlin"], "swift": ["swift"], "php": ["php"],
    "ruby": ["ruby"], "r": ["r programming", "r language", "rstudio"], "matlab": ["matlab"], "scala": ["scala"],
    "sql": ["sql", "t-sql", "pl/sql"], "bash": ["bash", "shell scripting"],
    # web
    "html": ["html", "html5"], "css": ["css", "css3"], "react": ["react", "react.js", "reactjs"],
    "angular": ["angular"], "vue": ["vue", "vue.js"], "node.js": ["node.js", "nodejs", "node"],
    "django": ["django"], "flask": ["flask"], "fastapi": ["fastapi"], "spring": ["spring boot", "spring"],
    ".net": [".net", "asp.net"], "rest api": ["rest api", "restful", "rest apis"], "graphql": ["graphql"],
    # data and AI
    "machine learning": ["machine learning", "ml"], "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"], "computer vision": ["computer vision"],
    "pytorch": ["pytorch"], "tensorflow": ["tensorflow"], "keras": ["keras"], "scikit-learn": ["scikit-learn", "sklearn"],
    "pandas": ["pandas"], "numpy": ["numpy"], "data analysis": ["data analysis", "data analytics"],
    "data visualization": ["data visualization", "data visualisation"], "statistics": ["statistics", "statistical analysis"],
    "power bi": ["power bi", "powerbi"], "tableau": ["tableau"], "excel": ["excel", "microsoft excel"],
    "spark": ["spark", "pyspark"], "hadoop": ["hadoop"], "llm": ["llm", "large language models"],
    # databases and cloud
    "postgresql": ["postgresql", "postgres"], "mysql": ["mysql"], "mongodb": ["mongodb"], "oracle": ["oracle"],
    "redis": ["redis"], "aws": ["aws", "amazon web services"], "azure": ["azure"], "gcp": ["gcp", "google cloud"],
    "docker": ["docker"], "kubernetes": ["kubernetes", "k8s"], "git": ["git", "github", "gitlab"],
    "linux": ["linux"], "ci/cd": ["ci/cd", "continuous integration"], "terraform": ["terraform"],
    # security and networks
    "cybersecurity": ["cybersecurity", "cyber security", "information security"], "networking": ["networking", "tcp/ip"],
    # design and product
    "figma": ["figma"], "ui/ux": ["ui/ux", "ux design", "ui design", "user experience"],
    "agile": ["agile", "scrum", "kanban"], "project management": ["project management", "pmp"],
    "jira": ["jira"], "testing": ["unit testing", "software testing", "pytest", "junit", "selenium"],
    # business
    "accounting": ["accounting"], "marketing": ["marketing", "digital marketing"], "sales": ["sales"],
    "customer service": ["customer service", "customer support"], "sap": ["sap"], "crm": ["crm", "salesforce"],
    # soft skills
    "communication": ["communication"], "teamwork": ["teamwork", "team player", "collaboration"],
    "leadership": ["leadership"], "problem solving": ["problem solving", "problem-solving"],
    "time management": ["time management"], "critical thinking": ["critical thinking"],
    # languages
    "arabic": ["arabic"], "english": ["english"], "french": ["french"],
}

# Short or ambiguous spellings matched only in a skills section, to avoid false hits in normal prose
CONTEXT_ONLY = {"js", "ml", "r programming", "go", "node", "spring", "rust", "swift", "oracle", "sales", "c language",
                "communication", "english", "arabic", "french"}

SECTION_HEADINGS: dict[str, list[str]] = {
    "summary": ["summary", "profile", "professional summary", "about me", "objective", "career objective"],
    "experience": ["experience", "work experience", "professional experience", "employment", "employment history",
                   "work history", "internships", "internship"],
    "education": ["education", "academic background", "qualifications", "academic qualifications"],
    "skills": ["skills", "technical skills", "core skills", "key skills", "competencies", "core competencies",
               "tools", "technologies", "soft skills"],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses", "courses", "training"],
    "languages": ["languages"],
    "awards": ["awards", "achievements", "honors", "honours"],
    "volunteering": ["volunteering", "volunteer experience", "activities", "extracurricular activities"],
    "publications": ["publications", "research"],
    "references": ["references"],
}
