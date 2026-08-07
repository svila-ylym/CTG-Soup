"""
SMTP 邮件服务模块
用于发送验证邮件、重置密码邮件、通知邮件等
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from fastapi import HTTPException, status
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SMTPService:
    """SMTP 邮件服务类"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
    
    def _create_connection(self) -> smtplib.SMTP:
        """创建 SMTP 连接"""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()  # 启用 TLS 加密
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"SMTP 连接失败：{str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="邮件服务暂时不可用"
            )
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 格式邮件内容
            text_content: 纯文本格式邮件内容（可选）
        
        Returns:
            bool: 发送是否成功
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # 添加纯文本版本
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(part1)
            
            # 添加 HTML 版本
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)
            
            server = self._create_connection()
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"邮件发送成功：{to_email}, 主题：{subject}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败：{to_email}, 错误：{str(e)}")
            return False
    
    def send_verification_email(self, to_email: str, username: str, verification_code: str) -> bool:
        """
        发送邮箱验证邮件
        
        Args:
            to_email: 收件人邮箱
            username: 用户名
            verification_code: 验证码
        
        Returns:
            bool: 发送是否成功
        """
        subject = f"【海龟汤社区】邮箱验证 - {username}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .code {{ background: #fff; border: 2px dashed #667eea; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; color: #667eea; margin: 20px 0; border-radius: 5px; }}
                .footer {{ background: #333; color: #fff; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🐢 海龟汤社区</h1>
                    <p>欢迎加入我们的解谜世界</p>
                </div>
                <div class="content">
                    <h2>亲爱的 {username}：</h2>
                    <p>感谢您注册海龟汤社区！为了完成账号验证，请使用以下验证码：</p>
                    <div class="code">{verification_code}</div>
                    <p>验证码有效期为 30 分钟。请勿将此验证码透露给他人。</p>
                    <p>如果这不是您本人的操作，请忽略此邮件。</p>
                    <a href="{settings.APP_URL or 'http://localhost:5173'}/verify-email?code={verification_code}" class="button">立即验证</a>
                </div>
                <div class="footer">
                    <p>© 2026 SkyUnreal Lab. 保留所有权利。</p>
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        亲爱的 {username}：
        
        感谢您注册海龟汤社区！
        
        您的验证码是：{verification_code}
        
        验证码有效期为 30 分钟。
        
        如果这不是您本人的操作，请忽略此邮件。
        
        © 2026 SkyUnreal Lab. 保留所有权利。
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """
        发送重置密码邮件
        
        Args:
            to_email: 收件人邮箱
            username: 用户名
            reset_token: 重置令牌
        
        Returns:
            bool: 发送是否成功
        """
        subject = "【海龟汤社区】重置密码"
        
        reset_link = f"{settings.APP_URL or 'http://localhost:5173'}/reset-password?token={reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #f5576c; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ background: #333; color: #fff; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 密码重置</h1>
                    <p>海龟汤社区安全中心</p>
                </div>
                <div class="content">
                    <h2>亲爱的 {username}：</h2>
                    <p>您请求重置海龟汤社区的账号密码。请点击下方按钮进行重置：</p>
                    <a href="{reset_link}" class="button">重置密码</a>
                    <div class="warning">
                        <strong>⚠️ 安全提示：</strong>
                        <ul>
                            <li>此链接有效期为 1 小时</li>
                            <li>如非本人操作，请立即修改密码并检查账号安全</li>
                            <li>请勿将此链接透露给他人</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2026 SkyUnreal Lab. 保留所有权利。</p>
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        亲爱的 {username}：
        
        您请求重置海龟汤社区的账号密码。
        
        请访问以下链接重置密码：
        {reset_link}
        
        此链接有效期为 1 小时。
        
        如非本人操作，请立即修改密码并检查账号安全。
        
        © 2026 SkyUnreal Lab. 保留所有权利。
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_notification_email(
        self,
        to_email: str,
        username: str,
        notification_type: str,
        title: str,
        content: str
    ) -> bool:
        """
        发送通知邮件
        
        Args:
            to_email: 收件人邮箱
            username: 用户名
            notification_type: 通知类型
            title: 通知标题
            content: 通知内容
        
        Returns:
            bool: 发送是否成功
        """
        subject = f"【海龟汤社区】{title}"
        
        type_icons = {
            "mention": "@",
            "comment_reply": "💬",
            "system": "📢",
            "achievement": "🏆",
        }
        
        icon = type_icons.get(notification_type, "📧")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .notification {{ background: #fff; border-left: 4px solid #4facfe; padding: 15px; margin: 20px 0; }}
                .footer {{ background: #333; color: #fff; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} {title}</h1>
                    <p>您有一条新的通知</p>
                </div>
                <div class="content">
                    <h2>亲爱的 {username}：</h2>
                    <div class="notification">
                        <p>{content}</p>
                    </div>
                    <p>登录海龟汤社区查看更多详情。</p>
                </div>
                <div class="footer">
                    <p>© 2026 SkyUnreal Lab. 保留所有权利。</p>
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# 单例实例
smtp_service = SMTPService()


def get_smtp_service() -> SMTPService:
    """获取 SMTP 服务实例"""
    return smtp_service
