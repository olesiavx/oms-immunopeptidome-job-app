from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField(
    "Email",
    validators=[DataRequired(), Length(max=255)]
)
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = StringField(
    "Email",
    validators=[DataRequired(), Length(max=255)]
)
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")
    
class LogoutForm(FlaskForm):
    submit = SubmitField("Log out")

class CSRFOnlyForm(FlaskForm):
    pass