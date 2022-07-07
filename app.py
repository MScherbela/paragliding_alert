import datetime
import flask_security
import flask_login
import utils
import flask
from extensions import db, scheduler, mail, init_extensions
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, TimeField, IntegerField, BooleanField
from wtforms.validators import DataRequired
from flask_security.decorators import login_required, current_user
from models import Location, ConditionFilter, User
import weather
import plotly.graph_objects as go
from alerts import send_paragliding_alert
import logging

logging.basicConfig("/logs/paragliding_alert.log", level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
init_extensions(app)


@flask_login.user_logged_in.connect_via(app)
def add_condition_filter_if_not_exists(app, user):
    if user.condition_filter is None:
        user.condition_filter = ConditionFilter(user_id=user.id)
        db.session.commit()


def retrieve_all_weather_data():
    locations = Location.query.filter_by(active=True).all()
    for l in locations:
        fname = weather.get_weather_fname(l.id)
        weather.retrieve_weather_data(l.lat, l.lon, fname)


def send_all_paragliding_alerts():
    N_DAYS_MAX = 4
    for user in User.query.all():
        _, daily_data = get_weather_data_for_user(user)
        flyable_locations = []
        for loc in daily_data:
            flyable_days = [d for d, s in zip(loc['days'][:N_DAYS_MAX], loc['status'][:N_DAYS_MAX]) if s >= weather.WeatherStatus.MAYBE]
            if flyable_days:
                flyable_locations.append(dict(name=loc['name'], days=flyable_days))
        if flyable_locations:
            send_paragliding_alert(mail, user.email, flyable_locations)


class AddLocationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    lat = FloatField("Latitude", validators=[DataRequired()])
    lon = FloatField("Longitude", validators=[DataRequired()])
    submit = SubmitField("Add location")

class ConditionFilterForm(FlaskForm):
    max_wind = FloatField("Max. wind [km/h]", validators=[DataRequired()])
    max_gust = FloatField("Max. gust [km/h]", validators=[DataRequired()])
    max_prec = FloatField("Max. precipitation [mm/h]", validators=[DataRequired()])
    submit = SubmitField("Save changes")
    start_time_weekday = TimeField("Start time Mon-Thu", validators=[DataRequired()])
    start_time_friday = TimeField("Start time Friday", validators=[DataRequired()])
    start_time_weekend = TimeField("Start time Sat-Sun", validators=[DataRequired()])
    end_time = TimeField("End time", validators=[DataRequired()])
    min_window = IntegerField("Minimum flyable window [h]", validators=[DataRequired()])
    can_weekday = BooleanField("Alerts for Mon-Thu")
    can_friday = BooleanField("Alerts for Friday")
    can_weekend = BooleanField("Alerts for Sat-Sun")

def get_weather_data_for_user(user):
    user_locations = Location.query.filter_by(active=True, user_id=user.id).all()
    hourly_data = []
    daily_data = []

    for loc in user_locations:
        data_h = weather.parse_weather_data(weather.get_weather_fname(loc.id))
        status = [weather.is_flyable(d, user.condition_filter) for d in data_h]
        t, wind, gust = zip(*[(d.time, d.wind, d.gust) for d in data_h])
        hourly_data.append(dict(name=loc.name, t=t, wind=wind, gust=gust, status=status))

        days, status = weather.get_daily_flight_status(t, status, user.condition_filter.min_window)
        daily_data.append(dict(name=loc.name, days=days, status=status))
    return hourly_data, daily_data


# %% Scheduler tasks
@scheduler.task(trigger='cron', hour="6,19")
def update_weather():
    with app.app_context():
        retrieve_all_weather_data()
        send_all_paragliding_alerts()


# %% Views
@app.route('/add_location', methods=['GET', 'POST'])
@login_required
def add_location():
    logging.info("Test")
    form = AddLocationForm()

    if form.submit.data and form.validate():
        loc = Location(name=form.name.data, lat=form.lat.data, lon=form.lon.data, user_id=current_user.id)
        db.session.add(loc)
        db.session.commit()
        weather.retrieve_weather_data(loc.lat, loc.lon, weather.get_weather_fname(loc.id))
        flask.flash("Location added successfully", "success")

    return flask.render_template('add_location.html', form=form)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ConditionFilterForm(obj=current_user.condition_filter)
    if form.submit.data and form.validate():
        form.populate_obj(current_user.condition_filter)
        db.session.commit()
    return flask.render_template('settings.html', form=form)


@app.route('/', methods=['GET'])
@login_required
def index():
    hourly_data, daily_data = get_weather_data_for_user(current_user)
    if len(daily_data) == 0:
        return flask.redirect("/add_location")

    graphs = []
    for data_h, data_d in zip(hourly_data, daily_data):
        COLORS = ['red', 'yellow', 'green']
        fig = go.Figure()
        for day, s in zip(data_d['days'], data_d['status']):
            fig.add_vrect(day + datetime.timedelta(hours=7),
                          day + datetime.timedelta(hours=22),
                          line_width=0,
                          fillcolor=COLORS[s],
                          annotation_text=f"<b>{utils.WEEKDAYS[day.weekday()]}</b><br>{day.day}.{day.month}.",
                          annotation_position="top left",
                          opacity=0.25)
        fig.add_trace(go.Scatter(x=data_h['t'], y=data_h['wind'], name="Wind", line=dict(color='darkblue')))
        fig.add_trace(go.Scatter(x=data_h['t'], y=data_h['gust'], name="Gusts", line=dict(color='cornflowerblue', dash='dot')))
        fig.update_layout(go.Layout(paper_bgcolor='white',
                                    plot_bgcolor='white',
                                    height=300,
                                    margin=dict(t=0,b=0,l=0,r=0)))
        fig.update_yaxes(title="km/h", range=[-1, 40], showgrid=True, gridcolor='lightgray', nticks=5)
        fig.update_xaxes(showticklabels=False)
        graphs.append(fig.to_json())
    graphs = "[" + ",".join(graphs) + "]"
    location_names = [d['name'] for d in daily_data]
    return flask.render_template('index.html', graphs=graphs, daily_data=daily_data, location_names=location_names)


@app.route('/test', methods=['GET', 'POST'])
@flask_security.roles_required('admin')
def test():
    if flask.request.method == 'POST':
        if 'reload_weather' in flask.request.form.keys():
            retrieve_all_weather_data()
        if 'send_alerts' in flask.request.form.keys():
            send_all_paragliding_alerts()
    return flask.render_template('test.html')
