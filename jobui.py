import streamlit as st
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection parameters
MONGODB_URI = "mongodb://localhost:27017/"
DB_NAME = "job_listings"
COLLECTION_NAME = "jobs"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
jobs_collection = db[COLLECTION_NAME]

# Initialize session state for the pages
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'jobs' not in st.session_state:
    st.session_state.jobs = []  # Initialize an empty list to store jobs


# Function to retrieve jobs from the MongoDB collection
def get_jobs_from_db():
    try:
        jobs = list(jobs_collection.find())
        for job in jobs:
            job['_id'] = str(job['_id'])  # Convert ObjectId to string
        return jobs
    except Exception as e:
        st.error(f"Error retrieving jobs from database: {e}")
        return []


# Function to delete a job from the MongoDB collection
def delete_job_from_db(job_id):
    try:
        jobs_collection.delete_one({"_id": ObjectId(job_id)})
        st.success("Job deleted successfully!")
    except Exception as e:
        st.error(f"Error deleting job: {e}")


# Function to add a new job to the MongoDB collection
def add_job_to_db(job_data):
    try:
        # Insert the new job into the collection
        jobs_collection.insert_one(job_data)
        st.success("Job added successfully!")
    except Exception as e:
        st.error(f"Error adding job: {e}")


# Page 1: Job Listings and Search
def page_1():
    st.title("Job Searching Web App")

    # Load jobs from the database into the session state
    if not st.session_state.jobs:
        st.session_state.jobs = get_jobs_from_db()

    search_term = st.text_input("Search for a job by title or company").lower()

    filtered_jobs = [job for job in st.session_state.jobs if
                     search_term in job['title'].lower() or search_term in job['postID'].lower()]

    if filtered_jobs:
        for job in filtered_jobs:
            st.subheader(f"Job Title: {job['title']}")
            st.write(f"Post ID: {job['postID']}")
            st.write(f"Experience: {job['experience']} years")
            st.write(f"Description: {job['description']}")

            # Display the logo below the job title if it exists
            if 'logo' in job and job['logo']:
                st.image(job['logo'], caption="Company Logo", width=100)  # Adjust width as needed

            # Delete button
            delete_button = st.button("Delete", key=f"delete_{job['_id']}")

            # Check if delete button is clicked
            if delete_button:
                delete_job_from_db(job['_id'])  # Delete the job from the database
                st.session_state.jobs.remove(job)  # Remove from session state
                st.experimental_rerun()  # Refresh the page to reflect changes

            st.write("---")
    else:
        if search_term:
            st.write("No matching jobs found.")
        else:
            st.write("No jobs have been added yet.")

    if st.button("ADD JOB"):
        st.session_state.page = 2  # Navigate to the add job page

    st.write("---")
    if st.session_state.page != 1:
        if st.button("Previous Page"):
            st.session_state.page -= 1


# Page 2: Add Job Form
def page_2():
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
            # Prepare the job data to be inserted
            new_job = {
                "title": job_title,
                "postID": postID_val,
                "experience": yrofexp_val,
                "description": job_desc,
                "logo": logo.getvalue() if logo else None  # Get binary data if logo is uploaded
            }
            add_job_to_db(new_job)  # Add job to the database
            st.session_state.page = 1  # Return to the job listing page after submitting

    # Navigation buttons
    st.write("---")
    if st.button("Previous Page"):
        st.session_state.page = 1


# Page Navigation Logic
if st.session_state.page == 1:
    page_1()
elif st.session_state.page == 2:
    page_2()
