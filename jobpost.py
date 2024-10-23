import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import bcrypt

# MongoDB connection parameters
MONGODB_URI = "mongodb://localhost:27017/"
DB_NAME = "job_listings"
USERS_COLLECTION = "users"
JOBS_COLLECTION = "jobs"
APPLICATIONS_COLLECTION = "applications"  # New collection for job applications

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db[USERS_COLLECTION]
jobs_collection = db[JOBS_COLLECTION]
applications_collection = db[APPLICATIONS_COLLECTION]

# Helper function: Hash the password using bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Helper function: Check if the password matches the hashed password
def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

# Initialize session state for login and page navigation
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = "user"  # Default role is 'user'
if 'page' not in st.session_state:
    st.session_state.page = "login"  # Default page is the login page
if 'selected_job_id' not in st.session_state:
    st.session_state.selected_job_id = None

# Function to register a new user
def register_user(username, password, role="user"):
    hashed_pw = hash_password(password)
    users_collection.insert_one({"username": username, "password": hashed_pw, "role": role})
    st.success("Registration successful! You can now log in.")

# Function to authenticate a user
def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if user and check_password(password, user['password']):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = user.get("role", "user")  # Get role, default is "user"
        st.session_state.page = "list_jobs"  # Redirect to job listings after login
        st.success(f"Welcome {username}!")
    else:
        st.error("Invalid username or password")

# Login Page
def login_page():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        authenticate_user(username, password)

    st.write("Don't have an account?")
    if st.button("Register"):
        st.session_state.page = "register"

# Register Page
def register_page():
    st.title("Register")

    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match!")
        else:
            if users_collection.find_one({"username": username}):
                st.error("Username already exists!")
            else:
                register_user(username, password)
                st.session_state.page = "login"

    if st.button("Back to Login"):
        st.session_state.page = "login"

# Logout Function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = "user"
    st.session_state.page = "login"

# Job Listings Page (Only accessible if logged in)
def job_listings_page():
    st.title("Job Searching Web App")

    st.write(f"Welcome, {st.session_state.username}")

    search_term = st.text_input("Search for a job by title or company").lower()

    # Fetch jobs from MongoDB
    jobs = list(jobs_collection.find())

    # Filter jobs based on search term
    filtered_jobs = [job for job in jobs if search_term in job['title'].lower() or search_term in job['postID'].lower()]

    if filtered_jobs:
        for job in filtered_jobs:
            st.subheader(f"Job Title: {job['title']}")
            st.write(f"Post ID: {job['postID']}")
            st.write(f"Experience: {job['experience']} years")
            st.write(f"Description: {job['description']}")
            st.write(f"Posted by: {job['created_by']}")

            # Display the uploaded logo with a specified width
            if job['logo']:
                st.image(job['logo'], caption="Company Logo", width=100)

            # Apply for Job button
            if st.button(f"Apply for {job['title']}", key=f"apply_{job['_id']}"):
                st.session_state.selected_job_id = job['_id']
                st.session_state.page = "apply_for_job"

            # Delete job button (visible only to the creator or an admin)
            if st.session_state.username == job['created_by'] or st.session_state.role == "admin":
                if st.button(f"Delete {job['title']}", key=str(job['_id'])):
                    delete_job(job['_id'])
                    st.success(f"Job '{job['title']}' has been deleted!")
                    st.experimental_rerun()  # Refresh the page after deleting the job
            st.write("---")
    else:
        if search_term:
            st.write("No matching jobs found.")
        else:
            st.write("No jobs have been added yet.")

    # Button to navigate to the Add Job page
    if st.button("ADD JOB"):
        st.session_state.page = "add_job"

    # Logout button
    if st.button("Logout"):
        logout()

# Add Job Page
def add_job_page():
    st.title("Add a Job")

    with st.form(key='add_job_form'):
        st.subheader("Add a New Job")

        job_title = st.text_input("Enter Job Title")
        postID, yrofexp = st.columns(2)

        postID_val = postID.text_input("Enter Post ID")
        yrofexp_val = yrofexp.text_input("Year of Experience")

        job_desc = st.text_area("Job Description")
        logo = st.file_uploader("Upload the Company Logo")  # Optional logo input

        # Submit button to add the job
        submit_button = st.form_submit_button(label="Submit")

        if submit_button and job_title and postID_val and yrofexp_val and job_desc:
            # Save job to MongoDB
            new_job = {
                "title": job_title,
                "postID": postID_val,
                "experience": yrofexp_val,
                "description": job_desc,
                "logo": logo.read() if logo else None,  # Store logo as binary
                "created_by": st.session_state.username  # Track who created the job
            }
            jobs_collection.insert_one(new_job)
            st.success(f"Job '{job_title}' has been added successfully!")
            st.session_state.page = "list_jobs"  # Return to the job listing page after submitting

    if st.button("Back to Listings"):
        st.session_state.page = "list_jobs"

# Apply for Job Page
def apply_for_job_page():
    st.title("Apply for Job")

    # Get the selected job from MongoDB
    selected_job = jobs_collection.find_one({"_id": ObjectId(st.session_state.selected_job_id)})

    if selected_job:
        st.subheader(f"Job Title: {selected_job['title']}")

        # Applicant form
        with st.form(key='apply_form'):
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            resume = st.file_uploader("Upload Your Resume", type=['pdf', 'docx'])

            submit_button = st.form_submit_button(label="Submit Application")

            if submit_button:
                if name and email and resume:
                    # Save the application to the database
                    new_application = {
                        "job_id": selected_job['_id'],
                        "job_title": selected_job['title'],
                        "applicant_name": name,
                        "applicant_email": email,
                        "resume": resume.read()  # Store resume file as binary data
                    }
                    applications_collection.insert_one(new_application)  # Store in applications collection

                    st.success("Application submitted successfully!")
                    st.session_state.page = "list_jobs"  # Go back to the job listings page after submission
                else:
                    st.error("Please complete all fields.")
    else:
        st.error("Job not found.")

    if st.button("Back to Job Listings"):
        st.session_state.page = "list_jobs"

# Function to delete a job post
def delete_job(job_id):
    jobs_collection.delete_one({"_id": ObjectId(job_id)})

# Page Navigation Logic
if st.session_state.logged_in:
    if st.session_state.page == "list_jobs":
        job_listings_page()
    elif st.session_state.page == "add_job":
        add_job_page()
    elif st.session_state.page == "apply_for_job":
        apply_for_job_page()
else:
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "register":
        register_page()
