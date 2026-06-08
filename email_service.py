# email_service.py
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_pipeline_email(state: dict) -> bool:
    """
    Handles adaptive asset assembly and SMTP transport.
    Dynamically falls back to text logs if structured DB tables are missing.
    """
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", "587"))
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")
    recipient = state.get("recipient_email")
    
    if not sender_email or not sender_password or not recipient:
        print("❌ Email skipped: Missing credentials or recipient address.")
        return False

    name = state.get("recipient_name", "User")
    target = state.get("email_target_type")
    
    # --- FIX 1: Normalize Swagger/Client default strings & infer target if ambiguous ---
    if target in ["string", "", None]:
        if state.get("blog_post"):
            target = "blog_post"
        elif state.get("db_results") and any(getattr(x, "columns", None) or getattr(x, "file_path", None) for x in state["db_results"]):
            target = "db_results"
        elif state.get("research_data"):
            target = "raw_research"
        else:
            target = "general_output"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    
    base_html_start = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #f3f4f6; padding: 20px;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #111827; padding: 25px; border-radius: 10px; border: 1px solid #374151;">
            <h2 style="color: #6366f1; border-bottom: 2px solid #374151; padding-bottom: 12px; margin-top: 0;">Multi Agent Graph API — Automated Dispatch</h2>
            <p style="color: #9ca3af;">Hello {name},</p>
            <p>Your requested agent pipeline assets have been successfully compiled:</p>
            <hr style="border: 0; border-top: 1px solid #374151; margin: 20px 0;" />
    """
    
    base_html_end = """
            <hr style="border: 0; border-top: 1px solid #374151; margin-top: 25px;" />
            <p style="font-size: 11px; color: #6b7280; text-align: center; margin-bottom: 0;">Orchestrated via multi-agent state topology.</p>
        </div>
    </body>
    </html>
    """
    
    body_content = ""
    
    try:
        # --- Polymorphic Content Assembly ---
        
        # NEW:  Scan message history backward to isolate the true query/operational output
        agent_text_output = "No operational text logs could be isolated."
        if state.get("messages"):
            for m in reversed(state["messages"]):
                m_content = getattr(m, "content", str(m))
                if m_content and not any(term in m_content for term in ["Notification payload", "successfully emailed", "Email skipped"]):
                    agent_text_output = m_content
                    break
        # Scenario A: DB Results Extraction
        if target == "db_results" and state.get("db_results"):
            latest_db = state["db_results"][-1]
            
            # Sub-scenario: It was a true SQL execution with structured table data
            if latest_db.columns and latest_db.rows:
                msg['Subject'] = "Agent Extract: Database Export & Query Execution"
                table_headers = "".join([f"<th style='padding: 10px; background-color: #1f2937; text-align: left; border: 1px solid #374151; color: #818cf8;'>{col}</th>" for col in latest_db.columns])
                table_rows = ""
                for row in latest_db.rows[:50]: # Cap preview at 50 rows
                    row_cells = "".join([f"<td style='padding: 8px; border: 1px solid #374151; color: #d1d5db;'>{str(cell)}</td>" for cell in row])
                    table_rows += f"<tr>{row_cells}</tr>"
                    
                body_content = f"""
                <h3 style="color: #34d399;">Structured Data Extract (Top Rows Preview)</h3>
                <p><strong>Executed SQL Query:</strong></p>
                <pre style="background-color: #030712; padding: 14px; border-left: 4px solid #34d399; color: #a7f3d0; font-family: monospace; overflow-x: auto;">{latest_db.sql}</pre>
                <p><strong>Total Row Count:</strong> {latest_db.row_count}</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px;">
                    <thead><tr>{table_headers}</tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
                <p style="font-size: 13px; color: #9ca3af; margin-top: 10px;">*The full dataset has been attached below as a structured Parquet file.</p>
                """
            else:
                # Sub-scenario fallback: It was a filesystem action (e.g., list files) recorded in message log
                msg['Subject'] = "Agent Extract: Filesystem / Command Execution Log"
                # last_msg = state["messages"][-1].content if state.get("messages") else "No output text generated."
                body_content = f"""
                <h3 style="color: #60a5fa;">Filesystem Operation Output</h3>
                <div style="background-color: #030712; padding: 16px; border-radius: 6px; border: 1px solid #374151; font-family: monospace; white-space: pre-wrap; color: #e5e7eb; line-height: 1.5;">{agent_text_output}</div>
                """
                
            # Process physical file attachments if paths exist
            if latest_db.file_path and os.path.exists(latest_db.file_path):
                with open(latest_db.file_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(latest_db.file_path)
                    part.add_header('Content-Disposition', f'attachment; filename={filename}')
                    msg.attach(part)

        # Scenario B: Written Blog Post / Summary Text
        elif target == "blog_post" and state.get("blog_post"):
            msg['Subject'] = "Agent Extract: Blog Post Content Draft"
            body_content = f"""
            <h3 style="color: #fb7185;">Generated Article Writeup</h3>
            <div style="background-color: #1f2937; padding: 20px; border-radius: 6px; border: 1px solid #374151; color: #e5e7eb; line-height: 1.6; white-space: pre-wrap;">{state['blog_post']}</div>
            """

        # Scenario C: Raw Web RAG Research Summaries
        elif target == "raw_research" and state.get("research_data"):
            msg['Subject'] = "Agent Extract: Semantic Web Research Analysis"
            latest_research = state["research_data"][-1]
            body_content = f"""
            <h3 style="color: #60a5fa;">Semantic RAG Intelligence Summary</h3>
            <div style="background-color: #1f2937; padding: 20px; border-radius: 6px; border: 1px solid #374151; color: #e5e7eb; line-height: 1.6; white-space: pre-wrap;">{latest_research}</div>
            """

        # Scenario D: Safety Fallback for General / Unmatched requests
        else:
            msg['Subject'] = "Agent Extract: Execution Output Summary"
            # last_msg = state["messages"][-1].content if state.get("messages") else "Workflow executed successfully with no trailing text context."
            body_content = f"""
            <h3 style="color: #9ca3af;">System Message Log</h3>
            <div style="background-color: #030712; padding: 16px; border-radius: 6px; border: 1px solid #374151; color: #e5e7eb; font-family: monospace; white-space: pre-wrap;">{agent_text_output}</div>
            """

        # Attach complete HTML assembly and deliver via SMTP
        msg.attach(MIMEText(base_html_start + body_content + base_html_end, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        print("✉️ Email dispatched successfully with all data metrics attached.")
        return True
        
    except Exception as e:
        print(f"❌ Email Service Error: {str(e)}")
        return False