import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
from streamlit_card import card
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns

def load_dataset():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books(
        bookID INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        authors TEXT,
        average_rating FLOAT,
        language_code TEXT,
        ratings_count INTEGER,
        publisher TEXT
    )''')
    try:
        df = pd.read_csv('books.csv', on_bad_lines='skip')
    except pd.errors.ParserError as e:
        st.error(f"Error loading CSV: {e}")
        return

    cursor.execute('DELETE FROM books')  # Clear the table before reloading the data

    for row in df.itertuples():
        cursor.execute('''
        INSERT INTO books (title, authors, average_rating, language_code, ratings_count, publisher)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (row.title, row.authors, row.average_rating, row.language_code, row.ratings_count, row.publisher))
    conn.commit()
    conn.close()


def create_user():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id VARCHAR UNIQUE,
        name TEXT,
        password VARCHAR
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS librarystaff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id VARCHAR UNIQUE,
        name TEXT,
        password VARCHAR
    )
    ''')
    test_data = [
        ('S001', 'Alice', 'password123'),
        ('S002', 'Bob', 'password456'),
        ('S003', 'Charlie', 'password789')
    ]
    cursor.executemany('''
    INSERT OR IGNORE INTO students (student_id, name, password) VALUES (?, ?, ?)
    ''', test_data)
    conn.commit()
    conn.close()


def student_register(student_id, name, password):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO students (student_id, name, password) VALUES (?, ?, ?)
    ''', (student_id, name, password))
    conn.commit()
    conn.close()


def check_credentials(student_id, name, password):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM students WHERE student_id = ? AND name = ? AND password = ?
    ''', (student_id, name, password))
    result = cursor.fetchone()
    conn.close()
    return result


def admin_register(employee_id, name, password):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO librarystaff (employee_id, name, password) VALUES (?, ?, ?)
    ''', (employee_id, name, password))
    conn.commit()
    conn.close()


def check_admin_credentials(employee_id, name, password):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM librarystaff WHERE employee_id = ? AND name = ? AND password = ?
    ''', (employee_id, name, password))
    result = cursor.fetchone()
    conn.close()
    return result


def fetch_books():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM books
    ''')
    books = cursor.fetchall()
    conn.close()
    return books

def fetch_loaned_books_by_date():
    conn = sqlite3.connect('students.db')
    query = '''
    SELECT loan_date, COUNT(*) as count
    FROM book_loans
    GROUP BY loan_date
    ORDER BY loan_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df



def get_recommendations(n=10):
    conn = sqlite3.connect('students.db')
    query = '''
    SELECT title, authors, average_rating FROM books
    WHERE average_rating < 5
    ORDER BY average_rating DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    df = df.sample(frac=1).reset_index(drop=True)  # Shuffle the DataFrame
    return df.head(n)


def random_personal_recommendations(user_id, n=5):
    books = fetch_books()
    if not books:
        return []
    df = pd.DataFrame(books, columns=['bookID', 'title', 'authors', 'average_rating', 'language_code', 'ratings_count', 'publisher'])
    random_books = df.sample(n)
    return random_books


def search_books(keyword, search_by):
    conn = sqlite3.connect('students.db')
    query = f"SELECT * FROM books WHERE {search_by} LIKE ?"
    df = pd.read_sql_query(query, conn, params=[f"%{keyword}%"])
    conn.close()
    return df

def create_book_loans():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS book_loans(
                   loan_id INTEGER PRIMARY KEY AUTOINCREMENT ,
                   student_id VARCHAR,
                   book_id INTEGER,
                   loan_date DATE,
                   return_date DATE,
                   FOREIGN KEY(student_id) REFERENCES students(student_id),
                   FOREIGN KEY (book_id) REFERENCES books(bookID))''')
    conn.commit()
    conn.close()


def issue_book(student_id, book_id):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    loan_date = datetime.now().date()
    
    # Check if the book exists
    cursor.execute('''
    SELECT title FROM books WHERE bookID = ?
    ''', (book_id,))
    book_name_row = cursor.fetchone()
    if book_name_row is None:
        conn.close()
        return None, f"No book found with ID {book_id}"
    
    book_name = book_name_row[0]

    # Issue the book
    cursor.execute('''
    INSERT INTO book_loans (student_id, book_id, loan_date, return_date) VALUES(?,?,?,NULL)''', (student_id, book_id, loan_date))
    conn.commit()
    conn.close()
    return book_name, None

def return_book(loan_id):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    return_date = datetime.now().date()
    cursor.execute('''
        UPDATE book_loans 
        SET return_date = ?
        WHERE loan_id = ?
        ''', (return_date, loan_id))
    conn.commit()
    conn.close()

def fetch_return_data_by_date():
    conn = sqlite3.connect('students.db')
    query = '''
    SELECT return_date, COUNT(*) as count
    FROM book_loans
    WHERE return_date IS NOT NULL
    GROUP BY return_date
    ORDER BY return_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df



def fetch_loaned_books(student_id=None):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    if student_id:
        cursor.execute('''
        SELECT book_loans.loan_id, books.title, books.authors, book_loans.loan_date, book_loans.return_date
        FROM book_loans
        JOIN books ON book_loans.book_id = books.bookID
        WHERE book_loans.student_id = ?
        ''', (student_id,))
    else:
        cursor.execute('''
        SELECT book_loans.loan_id, books.title, books.authors, book_loans.loan_date, book_loans.return_date, book_loans.student_id
        FROM book_loans
        JOIN books ON book_loans.book_id = books.bookID
        ''')
    books = cursor.fetchall()
    conn.close()
    return books

def fetch_return_data():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT bl.loan_id, bl.student_id, s.name, bl.book_id, b.title, bl.loan_date, bl.return_date
    FROM book_loans bl
    JOIN students s ON bl.student_id = s.student_id
    JOIN books b ON bl.book_id = b.bookID
    WHERE bl.return_date IS NOT NULL
    ''')
    return_data = cursor.fetchall()
    conn.close()
    return return_data

def fetch_all_users():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('SELECT student_id, name FROM students')
    students = cursor.fetchall()
    conn.close()
    return students

def fetch_books_availability():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT b.bookID, b.title, b.authors, 
           CASE 
               WHEN bl.loan_id IS NULL THEN 'Available' 
               ELSE 'Loaned Out' 
           END AS status
    FROM books b
    LEFT JOIN book_loans bl ON b.bookID = bl.book_id AND bl.return_date IS NULL
    ''')
    books_availability = cursor.fetchall()
    conn.close()
    return books_availability
def main():
    st.sidebar.title("NAVIGATION BAR")
    with st.sidebar.expander("Menu", expanded=True):
        page = option_menu(
            menu_title="Navigation",
            options=["Register", "Login", "Library", "Book Loans", "Dashboard"],
            icons=["house", "person", "book", "circle", "bar-chart"],
            menu_icon="cast",
            default_index=0
        )

    if page == "Register":
        st.title("STUDENT LIBRARY MANAGEMENT SYSTEM")
        st.header("Register according to your role in the organization")
        
        with st.expander("Student Registration", expanded=True):
            student_id = st.text_input("Student ID")
            student_name = st.text_input("Student Name")
            student_password = st.text_input("Created Password", type='password')
            student_register_button = st.button("Register as Student")

            if student_register_button:
                if not student_id or not student_name or not student_password:
                    st.error("Please fill out all fields.")
                else:
                    try:
                        student_register(student_id, student_name, student_password)
                        st.success(f"Registration successful, welcome {student_name}!")
                    except sqlite3.IntegrityError:
                        st.error("Student ID already exists. Please choose a different ID.")
        
        with st.expander("Admin Registration", expanded=True):
            employee_id = st.text_input("Employee ID")
            admin_name = st.text_input("Employee Name")
            admin_password = st.text_input("Password", type='password')
            admin_register_button = st.button("Register as Admin")

            if admin_register_button:
                if not employee_id or not admin_name or not admin_password:
                    st.error("Please fill out all fields.")
                else:
                    try:
                        admin_register(employee_id, admin_name, admin_password)
                        st.success(f"Registration successful, welcome {admin_name}!")
                    except sqlite3.IntegrityError:
                        st.error("Employee ID already exists. Please choose a different ID.")

    elif page == "Login":
        st.title("STUDENT LIBRARY MANAGEMENT SYSTEM")
        st.header("Login according to your role in the organization")
        
        with st.expander("Student Login", expanded=True):
            student_id = st.text_input("Student ID")
            student_name = st.text_input("Student Name")
            student_password = st.text_input("Password", type='password')
            student_login_button = st.button("Login as Student")

            if student_login_button:
                user = check_credentials(student_id, student_name, student_password)
                if user:
                    st.success(f"Welcome, {student_name}!")
                    st.session_state["user_role"] = "student"
                    st.session_state["user_id"] = student_id
                    st.session_state["user_name"] = student_name
                else:
                    st.error("Invalid Student ID, Name, or Password")
        
        with st.expander("Admin Login", expanded=True):
            employee_id = st.text_input("Employee ID")
            admin_name = st.text_input("Employee Name")
            admin_password = st.text_input(" Registered Password", type='password')
            admin_login_button = st.button("Login as Admin")

            if admin_login_button:
                user = check_admin_credentials(employee_id, admin_name, admin_password)
                if user:
                    st.success(f"Welcome, {admin_name}!")
                    st.session_state["user_role"] = "admin"
                    st.session_state["user_id"] = employee_id
                    st.session_state["user_name"] = admin_name
                else:
                    st.error("Invalid Employee ID, Name, or Password")
    
    elif page == "Library":
        st.header("Library")
        load_dataset()  
        books = fetch_books()
        if books:
            with st.expander("Book Database", expanded=True):
                df = pd.DataFrame(books, columns=['Book ID', 'Title', 'Authors', 'Average Rating', 'Language Code', 'Ratings Count', 'Publisher'])
                st.dataframe(df)

            selected2 = option_menu("LIBRARY ENGINE", ["Popularity-Based Recommendations", "Personal Recommendations", "Book Search"], 
                                    icons=['broadcast', 'person', 'search'], 
                                    menu_icon="cast", default_index=0, orientation="horizontal")
            
            if selected2 == "Popularity-Based Recommendations":
                st.write("### Popularity-based Recommendations")
                num_recommendations = st.slider("Number of recommendations", 1, 20, 10)
                if st.button("Get Popular Books"):
                    recommendations = get_recommendations(num_recommendations)
                    if not recommendations.empty:
                        st.write("### Popular Books")
                        for index, row in recommendations.iterrows():
                            res = card(
                                title=row['title'],
                                text=f"by {row['authors']} (Rating: {row['average_rating']})",
                                styles={
                                    "card": {
                                        "width": "100%",
                                        "height": "300px"
                                    }
                                }
                            )
                            st.markdown(res)
                    else:
                        st.warning("No books found in the database.")
                    
            if selected2 == "Personal Recommendations":
                st.write("### Personal Recommendations")
                user_id = st.text_input("Enter your user ID for personal recommendations")
                num_recommendations = st.selectbox("Number of personal recommendations", [5, 10, 15, 20])
                if st.button("Get Personal Recommendations"):
                    if user_id:
                        recommendations = random_personal_recommendations(user_id, num_recommendations)
                        if not recommendations.empty:
                            st.write("### Recommended Books for You")
                            for index, row in recommendations.iterrows():
                                res = card(
                                    title=row['title'],
                                    text=f"by {row['authors']} (Rating: {row['average_rating']})",
                                    styles={
                                        "card": {
                                            "width": "100%",
                                            "height": "300px"
                                        }
                                    }
                                )
                                st.markdown(res)
                        else:
                            st.warning("No books found in the database.")
                    else:
                        st.error("Please enter your user ID.")

            if selected2 == "Book Search":
                st.write("### Book Search")
                search_by = st.selectbox("Search by", ["authors", "publisher", "average_rating"])
                keyword = st.text_input(f"Enter the {search_by}")
                if st.button("Search"):
                    results = search_books(keyword, search_by)
                    if not results.empty:
                        st.write("### Search Results")
                        for index, row in results.iterrows():
                            res = card(
                                title=row['title'],
                                text=f"by {row['authors']} (Rating: {row['average_rating']})",
                                styles={
                                    "card": {
                                        "width": "100%",
                                        "height": "300px"
                                    }
                                }
                            )
                            st.markdown(res)
                    else:
                        st.warning("No books found for the given search criteria.")
    elif page == "Book Loans":
        st.header("Book Loans")

        if "user_role" in st.session_state:
            if st.session_state["user_role"] == "student":
                student_id = st.session_state["user_id"]
                st.write(f"Logged in as {st.session_state['user_name']} (Student)")

                with st.expander("Book Database", expanded=True):
                    books = fetch_books()
                    if books:
                        df = pd.DataFrame(books, columns=['Book ID', 'Title', 'Authors', 'Average Rating', 'Language Code', 'Ratings Count', 'Publisher'])
                        st.dataframe(df)
                    else:
                        st.write("No books available in the library.")
                
                with st.expander("Book Availability",expanded=True):
                    book_avail = fetch_books_availability()
                    if book_avail:
                        df = pd.DataFrame(book_avail,columns=['Book ID', 'Title', 'Authors', 'Status'])
                        st.dataframe(df)
                    else:
                        st.write("No books found in the database")

                with st.expander("Issue Book", expanded=True):
                    book_id = st.number_input("Book ID", min_value=1, step=1)
                    if st.button("Issue Book"):
                        book_name, error_message = issue_book(student_id, book_id)
                        if error_message:
                            st.error(error_message)
                        else:
                            st.success(f"Book '{book_name}' with ID {book_id} issued successfully.")

                with st.expander("Return Book", expanded=True):
                    loan_id = st.number_input("Loan ID", min_value=1, step=1)
                    if st.button("Return Book"):
                        return_book(loan_id)
                        st.success(f"Book with Loan ID {loan_id} returned successfully.")

                with st.expander("My Loaned Books", expanded=True):
                    loaned_books = fetch_loaned_books(student_id)
                    if loaned_books:
                        df = pd.DataFrame(loaned_books, columns=['Loan ID', 'Title', 'Authors', 'Loan Date', 'Return Date'])
                        st.dataframe(df)
                    else:
                        st.write("You have no loaned books.")

            elif st.session_state["user_role"] == "admin":
                st.write(f"Logged in as {st.session_state['user_name']} (Admin)")

                with st.expander("View All Loaned Books", expanded=True):
                    loaned_books = fetch_loaned_books()
                    if loaned_books:
                        df = pd.DataFrame(loaned_books, columns=['Loan ID', 'Title', 'Authors', 'Loan Date', 'Return Date', 'Student ID'])
                        st.dataframe(df)
                    else:
                        st.write("No loaned books found.")
                    loaned_by_date = fetch_loaned_books_by_date()
                    if not loaned_by_date.empty:
                        st.write("### Loaned Books by date")
                        st.line_chart(loaned_by_date.set_index('loan_date'))
                with st.expander("Loaning Information",expanded=True):
                    return_data =  fetch_return_data()
                    if return_data:
                        df = pd.DataFrame(return_data,columns = ['Loan ID','Student ID','Student Name','Book ID','Book Title','Loan Date','Return Date'])
                        st.dataframe(df)
                    else:
                        st.write("No return data found")
                    return_by_date = fetch_return_data_by_date()
                    if not return_by_date.empty:
                        st.write(" ### Returned Books by Date")
                        st.line_chart(return_by_date.set_index('return_date'))
                    
                
                with st.expander("Display All Students",expanded=True):
                    students = fetch_all_users()
                    if students:
                        df = pd.DataFrame(students,columns=['Students ID','Name'])
                        st.dataframe(df)
                    else:
                        st.write("No registered students found")
    elif page == "Dashboard":
        st.title("Library DashBoard")
        if "user_role" in st.session_state:
            if st.session_state["user_role"] == "student":
                student_id = st.session_state["user_id"]
                st.subheader("Students don't have access to the dashboard")
            
            elif st.session_state["user_role"] == "admin":
                st.subheader("Admin Dashboard")
                
                loan_data = fetch_loaned_books_by_date()
                return_data = fetch_return_data_by_date()

                if not loan_data.empty and not return_data.empty:
                    loan_df = loan_data.rename(columns={'loan_date': 'Date', 'count': 'Count'})
                    return_df = return_data.rename(columns={'return_date': 'Date', 'count': 'Count'})
                    
                    
                    st.subheader("Books Loaned Over Time")
                    fig, ax = plt.subplots()
                    loan_df.plot(x='Date', y='Count', ax=ax, legend=False)
                    ax.set_title('Books Loaned Over Time')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Count')
                    st.pyplot(fig)


                    st.subheader("Books Returned Over Time")
                    fig, ax = plt.subplots()
                    return_df.plot(x='Date', y='Count', ax=ax, legend=False)
                    ax.set_title('Books Returned Over Time')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Count')
                    st.pyplot(fig)

                    st.subheader("Loaned vs Returned Books Over Time ")
                    combined_df = loan_df.merge(return_df, on='Date', how='outer', suffixes=('_loaned', '_returned')).fillna(0)
                    fig = px.line(combined_df, x='Date', y=['Count_loaned', 'Count_returned'], labels={'value': 'Count', 'variable': 'Type'})
                    fig.update_layout(title='Loaned vs Returned Books Over Time', xaxis_title='Date', yaxis_title='Count')
                    st.plotly_chart(fig)
                else:
                    st.write("No data available for loans and returns.")
            else:
                st.write("You are logged in as a student or you have not logged in as an admin")

if __name__ == '__main__':
    create_user()
    create_book_loans()
    main()