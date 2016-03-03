from flask import Flask, request, jsonify, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

computer_ip = "http://192.168.0.8"


# Tables


class Task(db.Model):
    mID = db.Column(db.Integer, primary_key=True, unique=True)
    mTask = db.Column(db.String())
    mDescription = db.Column(db.String())
    mAssignee = db.Column(db.String())
    mDueDate = db.Column(db.String())
    mTaskStatus = db.Column(db.String())
    mOwner = db.Column(db.String())

    def __init__(self, mTask, mDescription, mAssignee, mDueDate, mTaskStatus, mOwner):
        self.mTask = mTask
        self.mDescription = mDescription
        self.mAssignee = mAssignee
        self.mDueDate = mDueDate
        self.mTaskStatus = mTaskStatus
        self.mOwner = mOwner

    def __repr__(self):
        return '<Task %r>' % self.mID


class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user = db.Column(db.String())
    team = db.Column(db.String())

    def __init__(self, user, team):
        self.user = user
        self.team = team

    def __repr__(self):
        return '<TeamMember %r>' % self.id


class Team(db.Model):
    __bind_key__ = 'flex'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(), unique=True)
    owner = db.Column(db.String())

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner

    def __repr__(self):
        return '<Team %r>' % self.name


# Methods

def db_create_team_member(user, team):
    db.session.add(TeamMember(user, team))
    db.session.commit()


def check_if_valid_session(session_id):
    r = requests.post(computer_ip + ":1754/verifyLogin", json={"uuid": session_id})
    response = r.json()
    if response["response"] == "valid uuid":
        return True
    else:
        return False

# Routes
# The only route which should not require a valid uuid is login


@app.route('/newTask', methods=['POST'])
def app_task():
    data = request.json
    response = {}
    try:
        mTask = data.get('mTask')
        mDescription = data.get('mDescription')
        mAssignee = data.get('mAssignee')
        mDueDate = data.get('mDueDate')
        uuid = data.get('uuid')
        mOwner = data.get('mOwner')  # Either "personal" or "team", if "team" then the task will be owned by the team
        # and you have to include 'mTeam'
        if mOwner == "personal":
            mOwner = uuid
            db.session.add(Task(mTask, mDescription, mAssignee, mDueDate, "To Do", mOwner))
            db.session.commit()
            response["response"] = "added personal task"
            response["status"] = "success"
            return jsonify(**response)
        elif mOwner == "team":
            try:
                mTeam = data.get('mTeam')  # The Team's ID
                mOwner = mTeam
                db.session.add(Task(mTask, mDescription, mAssignee, mDueDate, "To Do", mOwner))
                db.session.commit()
                response["response"] = "Added the task!"
                return jsonify(**response)
            except:
                response["response"] = "missing"
                return jsonify(**response)
    except:
        response["response"] = "missing"
        return jsonify(**response)


@app.route('/upgradeTask', methods=['POST'])
def upgrade_task():
    data = request.json
    response = {}
    try:
        mID = data.get('mID')
        uuid = data.get('uuid')
        task = Task.query.filter(Task.mID == mID).first()
        if check_if_valid_session(uuid) is not False and task.mOwner == uuid:
            if task.mTaskStatus == "To Do":
                task.mTaskStatus = "In Process"
            elif task.mTaskStatus == "In Process":
                task.mTaskStatus = "Done"
            db.session.commit()
            response["response"] = "Successfully upgraded task"
        else:
            response["status"] = "error"
            response["response"] = "You don't own this task!"
    except:
        response["response"] = "missing"

    return jsonify(**response)


@app.route('/getTasks', methods=['POST'])
def get_tasks():
    data = request.json
    response = {}

    try:
        uuid = data.get('uuid')
        scope = data.get('scope')
    except:
        response["response"] = "missing"
        return jsonify(**response)

    if check_if_valid_session(uuid) is not False:
        if scope == "personal":
            tasks = []
            isInitTodo = False
            isInitDoing = False
            isInitDone = False
            for task in Task.query.filter(Task.mOwner == uuid).all():
                if task.mTaskStatus == "To Do":
                    isInitTodo = True
                elif task.mTaskStatus == "In Process":
                    isInitDoing = True
                elif task.mTaskStatus == "Done":
                    isInitDone = True
                taskInfo = {'mTask': task.mTask,
                            'mDescription': task.mDescription,
                            'mAssignee': task.mAssignee,
                            'mDueDate': task.mDueDate,
                            'mID': task.mID,
                            'mTaskStatus': task.mTaskStatus
                            }
                tasks.append(taskInfo)
            response['tasks'] = tasks
            response['meta'] = {}
            response['meta']['isInitTodo'] = isInitTodo
            response['meta']['isInitDoing'] = isInitDoing
            response['meta']['isInitDone'] = isInitDone
            response["response"] = "success"
            response["status"] = "success"
        else:
            response["response"] = "not implemented yet"
            response["status"] = "error"
    else:
        response["response"] = "invalid uuid"

    return jsonify(**response)


@app.route('/deleteTask', methods=['POST'])
def delete_tank():
    data = request.json
    response = {}

    try:
        mID = data.get('mID')
        uuid = data.get('uuid')
        task = Task.query.filter(Task.mID == mID).first()
        if task is not None and task.mOwner == uuid:
            Task.query.filter(Task.mID == mID).delete()
            db.session.commit()
            response["response"] = "deleted task"
            response["status"] = "success"
        else:
            response["response"] = "You don't own this task or this task does not exist!"
            response["status"] = "error"
    except:
        response["response"] = "missing"
        response["status"] = "error"
    return jsonify(**response)


@app.route('/test', methods=['POST'])
def test():
    app.logger.debug("JSON received...")
    app.logger.debug(request.json)

    if request.json:
        data = request.json
        print(data.get('mTask'))
        return "Thanks. Your task is %s" % data.get("mTask")

    else:
        return "no json received"


@app.route('/verifyLogin', methods=['POST'])
def verify_login():
    data = request.json
    response = {}
    try:
        uuid = data.get('uuid')
        if check_if_valid_session(uuid):
            response["response"] = "valid uuid"
        else:
            response["response"] = "invalid uuid"
    except:
        response["response"] = "missing"

    return jsonify(**response)


@app.route('/refreshTask', methods=['POST'])
def refresh_task():
    data = request.json
    response = {}
    try:
        uuid = data.get('uuid')
        mID = data.get('mID')
    except:
        response['status'] = "missing"
        return jsonify(**response)

    try:
        task = Task.query.filter(Task.mID == mID).first()
        tasks = {'mTask': task.mTask,
                    'mDescription': task.mDescription,
                    'mAssignee': task.mAssignee,
                    'mDueDate': task.mDueDate,
                    'mID': task.mID,
                    'mTaskStatus': task.mTaskStatus
                    }
        response['tasks'] = tasks
        response['status'] = "success"
    except:
        response['status'] = "error"
        return jsonify(**response)

    return jsonify(**response)


@app.route('/updateTask', methods=['POST'])
def update_task():
    data = request.json
    response = {}
    try:
        mId = data.get('mID')
        mDescription = data.get('mDescription')
        mTitle = data.get('mTask')
        mAssignee = data.get('mAssignee')
        uuid = data.get('uuid')
        mDueDate = data.get('mDueDate')
    except:
        response["response"] = "missing"
        return jsonify(**response)

    task = Task.query.filter(Task.mID == mId).first()

    if task is not None and task.mOwner == uuid:
        try:
            task.mDescription = mDescription
            task.mTask = mTitle
            task.mAssignee = mAssignee
            task.mDueDate = mDueDate
            db.session.commit()
            response["response"] = "success"
            response["status"] = "success"
        except:
            response["response"] = "error"
            response["status"] = "error"
    else:
        response["response"] = "You don't own this task or this task does not exist"
        response["status"] = "error"

    return jsonify(**response)


@app.route('/joinTeam', methods=['POST'])
def join_team():
    data = request.json
    response = {}

    try:
        tID = data.get('tID')
        user = data.get('uuid')
        if check_if_valid_session(user):
            team = Team.query.filter(Team.id == tID).first()
            if team.freeJoin == "true":
                db_create_team_member(user, team.id)
            else:
                response["response"] = "freeJoin is not enabled"
        else:
            response["response"] = "invalid uuid"
    except:
        response["response"] = "missing"

    return jsonify(**response)


@app.route('/')
def testing_website():
    return render_template('index.html')


app.run(debug=True, host='0.0.0.0', port=7999)
