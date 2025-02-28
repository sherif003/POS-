# app.py
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os

# Set page config
st.set_page_config(page_title="نظام نقاط البيع - متجر ستوتا", layout="wide")

# SQLite setup
DB_FILE = "stota_store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT NOT NULL,
        original_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        stock INTEGER NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        products TEXT NOT NULL,
        total REAL NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        comment TEXT NOT NULL
    )''')
    
    conn.commit()
    conn.close()

# Load data from SQLite
def load_data():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    
    products = pd.read_sql_query("SELECT * FROM products", conn)
    if products.empty:
        products = pd.DataFrame(columns=["معرف المنتج", "اسم المنتج", "السعر الأصلي", "سعر البيع", "المخزون"])
    
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    if orders.empty:
        orders = pd.DataFrame(columns=["معرف الطلب", "التاريخ", "المنتجات", "الإجمالي"])
    
    expenses = pd.read_sql_query("SELECT * FROM expenses", conn)
    if expenses.empty:
        expenses = pd.DataFrame(columns=["معرف المصروف", "التاريخ", "المبلغ", "التعليق"])
    
    conn.close()
    return products, orders, expenses

# Save data to SQLite
def save_data(products, orders, expenses):
    conn = sqlite3.connect(DB_FILE)
    products.to_sql("products", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    expenses.to_sql("expenses", conn, if_exists="replace", index=False)
    conn.close()

# Sidebar menu
with st.sidebar:
    selected = option_menu(
        "القائمة الرئيسية",
        ["الرئيسية", "المنتجات", "الطلبات", "المصروفات", "الرؤى والإحصاءيات", "التصدير"],
        icons=["house", "box", "cart", "cash", "bar-chart", "download"],
        menu_icon="shop",
        default_index=0,
    )

products, orders, expenses = load_data()

# Pages
if selected == "الرئيسية":
    st.header("لوحة التحكم - متجر ستوتا")
    total_income = orders["الإجمالي"].sum() if not orders.empty else 0
    total_expenses = expenses["المبلغ"].sum() if not expenses.empty else 0
    product_costs = sum((products["سعر البيع"] - products["السعر الأصلي"]) * (products["المخزون"].max() - products["المخزون"])) if not products.empty else 0
    net_profit = total_income - product_costs - total_expenses
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي الدخل", f"{total_income:,.2f} ريال")
    with col2:
        st.metric("إجمالي المصروفات", f"{total_expenses:,.2f} ريال")
    with col3:
        st.metric("صافي الربح", f"{net_profit:,.2f} ريال")

elif selected == "المنتجات":
    st.header("إدارة المنتجات")
    search_term = st.text_input("ابحث عن منتج", "")
    if search_term:
        filtered_products = products[products["اسم المنتج"].str.contains(search_term, case=False, na=False)]
    else:
        filtered_products = products
    
    tab1, tab2 = st.tabs(["إضافة منتج", "تعديل المنتجات"])
    
    with tab1:
        with st.form("add_product"):
            product_id = st.text_input("معرف المنتج")
            product_name = st.text_input("اسم المنتج")
            original_price = st.number_input("السعر الأصلي", min_value=0.0, step=0.01)
            selling_price = st.number_input("سعر البيع", min_value=0.0, step=0.01)
            stock = st.number_input("المخزون", min_value=0, step=1)
            
            if st.form_submit_button("إضافة"):
                if not all([product_id, product_name]):
                    st.error("يرجى ملء جميع الحقول!")
                elif product_id in products["معرف المنتج"].values:
                    st.error("معرف المنتج موجود بالفعل!")
                else:
                    new_product = pd.DataFrame({
                        "معرف المنتج": [product_id],
                        "اسم المنتج": [product_name],
                        "السعر الأصلي": [original_price],
                        "سعر البيع": [selling_price],
                        "المخزون": [stock]
                    })
                    products = pd.concat([products, new_product], ignore_index=True)
                    save_data(products, orders, expenses)
                    st.success("تمت إضافة المنتج بنجاح!")
    
    with tab2:
        if not filtered_products.empty:
            st.dataframe(filtered_products)
            product_to_edit = st.selectbox("اختر المنتج للتعديل", filtered_products["معرف المنتج"])
            product_data = products[products["معرف المنتج"] == product_to_edit].iloc[0]
            
            with st.form("edit_product"):
                new_name = st.text_input("اسم المنتج", value=product_data["اسم المنتج"])
                new_original = st.number_input("السعر الأصلي", value=float(product_data["السعر الأصلي"]))
                new_selling = st.number_input("سعر البيع", value=float(product_data["سعر البيع"]))
                new_stock = st.number_input("المخزون", value=int(product_data["المخزون"]))
                
                if st.form_submit_button("حفظ التعديلات"):
                    products.loc[products["معرف المنتج"] == product_to_edit] = [
                        product_to_edit, new_name, new_original, new_selling, new_stock
                    ]
                    save_data(products, orders, expenses)
                    st.success("تم تعديل المنتج بنجاح!")

elif selected == "الطلبات":
    st.header("إدارة الطلبات")
    
    tab1, tab2 = st.tabs(["طلب جديد", "تعديل الطلبات"])
    
    with tab1:
        with st.form("new_order"):
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.write("المنتجات المتاحة:")
            for index, row in products.iterrows():
                st.write(f"{row['اسم المنتج']} - المخزون: {row['المخزون']} - السعر: {row['سعر البيع']} ريال")
            
            selected_products = st.multiselect("اختر المنتجات", products["اسم المنتج"])
            quantities = {}
            total_preview = 0
            if selected_products:
                st.write("معاينة الطلب:")
                for prod in selected_products:
                    qty = st.number_input(f"الكمية لـ {prod}", min_value=1, step=1, key=prod)
                    quantities[prod] = qty
                    price = products[products["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                    total_preview += price * qty
                st.write(f"الإجمالي المتوقع: {total_preview:,.2f} ريال")
            
            if st.form_submit_button("إنشاء الطلب"):
                if not selected_products:
                    st.error("يرجى اختيار منتج واحد على الأقل!")
                else:
                    total = 0
                    order_details = []
                    for prod in selected_products:
                        price = products[products["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                        qty = quantities[prod]
                        current_stock = products[products["اسم المنتج"] == prod]["المخزون"].iloc[0]
                        if qty > current_stock:
                            st.error(f"الكمية المطلوبة لـ {prod} ({qty}) أكبر من المخزون ({current_stock})!")
                            break
                        total += price * qty
                        order_details.append(f"{prod}: {qty}")
                        products.loc[products["اسم المنتج"] == prod, "المخزون"] -= qty
                    else:
                        new_order = pd.DataFrame({
                            "معرف الطلب": [order_id],
                            "التاريخ": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                            "المنتجات": [" | ".join(order_details)],
                            "الإجمالي": [total]
                        })
                        orders = pd.concat([orders, new_order], ignore_index=True)
                        save_data(products, orders, expenses)
                        st.success("تم إنشاء الطلب بنجاح!")
    
    with tab2:
        if not orders.empty:
            st.dataframe(orders)
            order_to_edit = st.selectbox("اختر الطلب للتعديل", orders["معرف الطلب"])
            order_data = orders[orders["معرف الطلب"] == order_to_edit].iloc[0]
            
            with st.form("edit_order"):
                st.write("المنتجات الحالية:", order_data["المنتجات"])
                selected_products = st.multiselect("تعديل المنتجات", products["اسم المنتج"],
                                                 default=[p.split(":")[0].strip() for p in order_data["المنتجات"].split(" | ")])
                quantities = {}
                total_preview = 0
                if selected_products:
                    for prod in selected_products:
                        default_qty = next((int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ") if p.startswith(prod)), 1)
                        qty = st.number_input(f"الكمية لـ {prod}", min_value=1, step=1, value=default_qty, key=f"edit_{prod}")
                        quantities[prod] = qty
                        price = products[products["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                        total_preview += price * qty
                    st.write(f"الإجمالي الجديد المتوقع: {total_preview:,.2f} ريال")
                
                if st.form_submit_button("حفظ التعديلات"):
                    # Revert old quantities to stock
                    old_items = {p.split(":")[0].strip(): int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ")}
                    for prod, qty in old_items.items():
                        products.loc[products["اسم المنتج"] == prod, "المخزون"] += qty
                    
                    # Apply new quantities
                    total = 0
                    order_details = []
                    for prod in selected_products:
                        price = products[products["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                        qty = quantities[prod]
                        current_stock = products[products["اسم المنتج"] == prod]["المخزون"].iloc[0]
                        if qty > current_stock:
                            st.error(f"الكمية المطلوبة لـ {prod} ({qty}) أكبر من المخزون ({current_stock})!")
                            break
                        total += price * qty
                        order_details.append(f"{prod}: {qty}")
                        products.loc[products["اسم المنتج"] == prod, "المخزون"] -= qty
                    else:
                        orders.loc[orders["معرف الطلب"] == order_to_edit] = [
                            order_to_edit, order_data["التاريخ"], " | ".join(order_details), total
                        ]
                        save_data(products, orders, expenses)
                        st.success("تم تعديل الطلب بنجاح!")

elif selected == "المصروفات":
    st.header("إدارة المصروفات")
    
    with st.form("add_expense"):
        amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
        comment = st.text_input("التعليق (مثل: نقل، كهرباء)")
        if st.form_submit_button("إضافة مصروف"):
            if not comment or amount <= 0:
                st.error("يرجى إدخال مبلغ صالح وتعليق!")
            else:
                new_expense = pd.DataFrame({
                    "معرف المصروف": [None],  # Auto-incremented by SQLite
                    "التاريخ": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "المبلغ": [amount],
                    "التعليق": [comment]
                })
                expenses = pd.concat([expenses, new_expense], ignore_index=True)
                save_data(products, orders, expenses)
                st.success("تمت إضافة المصروف بنجاح!")
    
    if not expenses.empty:
        st.dataframe(expenses)

elif selected == "الرؤى والإحصاءيات":
    st.header("الرؤى والإحصاءيات")
    
    if not orders.empty and not products.empty:
        total_income = orders["الإجمالي"].sum()
        total_expenses = expenses["المبلغ"].sum() if not expenses.empty else 0
        product_costs = sum((products["سعر البيع"] - products["السعر الأصلي"]) * (products["المخزون"].max() - products["المخزون"])) if not products.empty else 0
        net_profit = total_income - product_costs - total_expenses
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("إجمالي الدخل", f"{total_income:,.2f} ريال")
        with col2:
            st.metric("تكلفة المنتجات", f"{product_costs:,.2f} ريال")
        with col3:
            st.metric("المصروفات الإضافية", f"{total_expenses:,.2f} ريال")
        with col4:
            st.metric("صافي الربح", f"{net_profit:,.2f} ريال")
        
        # Improved Charts
        st.subheader("تحليل المبيعات")
        orders["التاريخ"] = pd.to_datetime(orders["التاريخ"])
        daily_sales = orders.groupby(orders["التاريخ"].dt.date)["الإجمالي"].sum().reset_index()
        fig1 = px.line(daily_sales, x="التاريخ", y="الإجمالي", title="المبيعات اليومية",
                      labels={"التاريخ": "التاريخ", "الإجمالي": "المبيعات (ريال)"})
        st.plotly_chart(fig1)
        
        # Product Sales Breakdown
        product_sales = pd.DataFrame()
        for _, row in orders.iterrows():
            items = row["المنتجات"].split(" | ")
            for item in items:
                name, qty = item.split(":")
                price = products[products["اسم المنتج"] == name.strip()]["سعر البيع"].iloc[0]
                product_sales = pd.concat([product_sales, pd.DataFrame({
                    "المنتج": [name.strip()],
                    "الكمية": [int(qty)],
                    "الإجمالي": [price * int(qty)]
                })], ignore_index=True)
        fig2 = px.bar(product_sales.groupby("المنتج").sum().reset_index(), 
                     x="المنتج", y="الإجمالي", title="المبيعات حسب المنتج",
                     labels={"المنتج": "اسم المنتج", "الإجمالي": "الإيرادات (ريال)"},
                     color="الكمية")
        st.plotly_chart(fig2)

elif selected == "التصدير":
    st.header("تصدير البيانات")
    
    export_type = st.selectbox("اختر نوع البيانات", ["المنتجات", "الطلبات", "المصروفات", "الكل"])
    if st.button("تصدير إلى CSV"):
        if export_type == "المنتجات":
            products.to_csv("exported_products.csv", index=False)
            st.download_button("تحميل", data=open("exported_products.csv", "rb"), file_name="exported_products.csv")
        elif export_type == "الطلبات":
            orders.to_csv("exported_orders.csv", index=False)
            st.download_button("تحميل", data=open("exported_orders.csv", "rb"), file_name="exported_orders.csv")
        elif export_type == "المصروفات":
            expenses.to_csv("exported_expenses.csv", index=False)
            st.download_button("تحميل", data=open("exported_expenses.csv", "rb"), file_name="exported_expenses.csv")
        else:
            with pd.ExcelWriter("stota_full_data.xlsx") as writer:
                products.to_excel(writer, sheet_name="المنتجات", index=False)
                orders.to_excel(writer, sheet_name="الطلبات", index=False)
                expenses.to_excel(writer, sheet_name="المصروفات", index=False)
            st.download_button("تحميل", data=open("stota_full_data.xlsx", "rb"), file_name="stota_full_data.xlsx")
        st.success("تم التصدير بنجاح!")
    
    st.subheader("إدارة قاعدة البيانات")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("تحميل قاعدة البيانات"):
            with open(DB_FILE, "rb") as f:
                st.download_button("تنزيل stota_store.db", f, file_name="stota_store.db")
            st.success("تم تحضير قاعدة البيانات!")
    with col2:
        uploaded_file = st.file_uploader("رفع قاعدة بيانات", type=["db"])
        if uploaded_file:
            with open(DB_FILE, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("تم رفع قاعدة البيانات! أعد تشغيل التطبيق.")
