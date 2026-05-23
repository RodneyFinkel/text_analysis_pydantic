"""
Email utilities for QuickRagAgent.
Handles email template generation and sending.
"""

import logging

def get_welcome_email_html(username: str) -> str:
    """Generate the welcome email HTML template with personalized username."""
    return f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    color: #ffffff;
                    line-height: 1.6;
                    background-color: #000000;
                    margin: 0;
                    padding: 0;
                }}
                p {{
                    color: #ffffff;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #1a1a1a;
                    border-radius: 8px;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #818cf8;
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }}
                .logo {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    object-fit: cover;
                    margin-bottom: 10px;
                }}
                .title {{
                    font-size: 28px;
                    font-weight: 600;
                    color: #ffffff;
                    margin: 10px 0;
                }}
                .content {{
                    padding: 20px 0;
                }}
                .greeting {{
                    font-size: 18px;
                    color: #818cf8;
                    font-weight: 600;
                    margin-bottom: 15px;
                }}
                .features {{
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #262626;
                    border-left: 4px solid #10b981;
                    border-radius: 4px;
                }}
                .feature-item {{
                    margin: 10px 0;
                    padding: 5px 0;
                    color: #ffffff;
                }}
                .feature-icon {{
                    margin-right: 8px;
                }}
                .cta-button {{
                    display: inline-block;
                    background-color: #818cf8;
                    color: #000000;
                    padding: 12px 30px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 15px;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid #404040;
                    margin-top: 30px;
                    color: #ffffff;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="cid:logo" alt="QuickRagAgent Logo" class="logo">
                    <div class="title">QuickRagAgent</div>
                    <p style="color: #9ca3af; margin: 0;">Voice AI RAG System</p>
                </div>
                
                <div class="content">
                    <div class="greeting">Welcome, {username}! 👋</div>
                    
                    <p>Thank you for signing up for <strong>QuickRagAgent</strong>. We're thrilled to have you on board!</p>
                    
                    <p>QuickRagAgent is a production-grade RAG stack combining:</p>
                    
                    <div class="features">
                        <div class="feature-item">
                            <span class="feature-icon">🎙️</span> <strong>Real-time Voice Input</strong> - Powered by Deepgram's high-fidelity speech recognition
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">⚡</span> <strong>Ultra-low Latency LLM</strong> - Groq LPU inference for instant responses
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">🔍</span> <strong>Hybrid Retrieval</strong> - Advanced semantic + BM25 search with reranking
                        </div>
                        <div class="feature-item">
                            <span class="feature-icon">📄</span> <strong>Document Management</strong> - Intelligent chunking and context extraction
                        </div>
                    </div>
                    
                    <p>Get started by uploading documents, configuring your retrieval settings, and begin asking questions with the power of AI at your fingertips.</p>
                    
                    <a href="http://localhost:5000/dashboard" class="cta-button">Launch Dashboard →</a>
                </div>
                
                <div class="footer">
                    <p>© 2026 QuickRagAgent. All rights reserved.<br>
                    Built by <a href="https://github.com/RodneyFinkel" style="color: #818cf8; text-decoration: none;">Rodney Finkel</a></p>
                </div>
            </div>
        </body>
    </html>
    """


def get_welcome_email_text(username: str) -> str:
    """Generate the welcome email plain text fallback."""
    return f"""Welcome, {username}!

Thank you for signing up for QuickRagAgent. We're excited to have you with us!

Visit your dashboard to get started: http://localhost:5000/dashboard

---
© 2026 QuickRagAgent. All rights reserved.
Built by Rodney Finkel (https://github.com/RodneyFinkel)
"""


def send_welcome_email(app, mail, email: str, username: str = 'User') -> None:
    """
    Send a welcome email to a new user.
    
    Args:
        app: Flask application instance
        mail: Flask-Mail Mail instance
        email: Recipient email address
        username: User's name for personalization
    """
    from flask_mail import Message
    
    try:
        # Validate email configuration
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            logging.error("Email configuration incomplete: MAIL_USERNAME or MAIL_PASSWORD not set in environment")
            return
        
        logging.info(f"Attempting to send welcome email to {email}")
        
        # Create message and send within application context so background
        # threads can access Flask's `current_app` and extensions.
        with app.app_context():
            msg = Message('Email Verification for QuickRagAgent Required', recipients=[email])
            
            # Plain text fallback
            msg.body = get_welcome_email_text(username)
            
            # Rich HTML email
            msg.html = get_welcome_email_html(username)
            
            # Attach logo from static folder
            with app.open_resource('static/aleph2.png') as logo_file:
                msg.attach('aleph.png', 'image/png', logo_file.read(), headers={'Content-ID': '<logo>'})
            
            mail.send(msg)
        logging.info(f"Welcome email sent successfully to {email}")
        
    except Exception as e:
        logging.error(f"Failed to send welcome email to {email}: {str(e)}", exc_info=True)
