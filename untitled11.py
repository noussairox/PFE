# -- coding: utf-8 --
"""Untitled11.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RJ73TJ1yDWDlTZAHVPnJs3kyBMqNBu_P
"""

from flask import Flask, render_template, Response , request ,session ,redirect,flash
import cv2
# import the necessary packages
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import os
from flask_admin import Admin  # pip install flask-admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.exceptions import abort
from flask_mail import Mail, Message



app = Flask(__name__)
admin = Admin(app)
mail = Mail(app)


app.config['SECRET_KEY'] = 'mysecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'maslernono@gmail.com'
app.config['MAIL_PASSWORD'] = 'maslernono-123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

class SecureModelView(ModelView):
    def is_accessible(self):
        if "logged_in" in session:
            return True
        else:
            abort(403)


# camera = cv2.VideoCapture('rtsp://freja.hiof.no:1935/rtplive/definst/hessdalen03.stream')  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera
# for local webcam use cv2.VideoCapture(0)


def detect_and_predict_mask(frame, faceNet, maskNet):
    # grab the dimensions of the frame and then construct a blob
    # from it
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224),
                                 (104.0, 177.0, 123.0))

    # pass the blob through the network and obtain the face detections
    faceNet.setInput(blob)
    detections = faceNet.forward()
    print(detections.shape)

    # initialize our list of faces, their corresponding locations,
    # and the list of predictions from our face mask network
    faces = []
    locs = []
    preds = []

    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with
        # the detection
        confidence = detections[0, 0, i, 2]

        # filter out weak detections by ensuring the confidence is
        # greater than the minimum confidence
        if confidence > 0.5:
            # compute the (x, y)-coordinates of the bounding box for
            # the object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # ensure the bounding boxes fall within the dimensions of
            # the frame
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # extract the face ROI, convert it from BGR to RGB channel
            # ordering, resize it to 224x224, and preprocess it
            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            # add the face and bounding boxes to their respective
            # lists
            faces.append(face)
            locs.append((startX, startY, endX, endY))

    # only make a predictions if at least one face was detected
    if len(faces) > 0:
        # for faster inference we'll make batch predictions on all
        # faces at the same time rather than one-by-one predictions
        # in the above `for` loop
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    # return a 2-tuple of the face locations and their corresponding
    # locations
    return (locs, preds)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'Admin' and request.form.get('password') == 'Admin-123456':
            session['logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('login.html', failed=True)
    return render_template('login.html')



def gen_frames():  # generate frame by frame from camera
    # load our serialized face detector model from disk
    prototxtPath = r"/Users/ASUS/OneDrive/Documents/Face Mask Detection/Face Mask Detection/face_detector/deploy.prototxt"
    #C:\Users\ASUS\OneDrive\Documents\Face Mask Detection\Face Mask Detection\face_detector
    weightsPath = r"/Users/ASUS/OneDrive/Documents/Face Mask Detection/Face Mask Detection/face_detector/res10_300x300_ssd_iter_140000.caffemodel"
    #prototxtPath = os.path.join(os.getcwd())
    #weightsPath = os.path.join(os.getcwd())
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
    # load the face mask detector model from disk
    maskNet = load_model("mask_detector.model")
    # initialize the video stream
    print("[INFO] starting video stream...")
    vs = cv2.VideoCapture(0)
    # loop over the frames from the video stream
    while True:
        # grab the frame from the threaded video stream and resize it
        # to have a maximum width of 400 pixels
           success,frame = vs.read()
           if not success:
                break
           if success:
            frame = imutils.resize(frame, width=1250)
            # detect faces in the frame and determine if they are wearing a
            # face mask or not
            (locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)
            # loop over the detected face locations and their corresponding
            # locations
            for (box, pred) in zip(locs, preds):
                   # unpack the bounding box and predictions
                (startX, startY, endX, endY) = box
                (mask, withoutMask) = pred
                # determine the class label and color we'll use to draw
                # the bounding box and text
                label = "Mask" if mask > withoutMask else "No Mask"
                color = (0, 255, 0) if label == "Mask" else (0, 0, 255)
                # include the probability in the label
                label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)
                # display the label and bounding box rectangle on the output
                # frame
                cv2.putText(frame, label, (startX, startY - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
                cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                # show the output frame
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                #cv2.imshow("Frame", frame)
                key = cv2.waitKey(1) & 0xFF
            # i the `q` key was pressed, break from the loop
                if key%256 == 32:
                    cv2.destroyAllWindows()
                    vs.stop()
                    break

        # do a bit of cleanup
   


@app.route('/video_feed')
def video_feed():
    # Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('home.html')

@app.route("/contact", methods=["GET", "POST"])
def contact():
    return render_template('contact_us.html')




@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')



if __name__ == '__main__':
    app.run(debug=True,port=5000)