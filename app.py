# app.py
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(page_title="نظام نقاط البيع - متجر ستوتا", layout="wide")

# SQLite setup
DB_FILE = "stota_store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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

def load_data():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    
    try:
        products = pd.read_sql_query("SELECT * FROM products", conn)
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        products = pd.DataFrame(columns=["معرف المنتج", "اسم المنتج", "السعر الأصلي", "سعر البيع", "المخزون"])
        products.to_sql("products", conn, if_exists="replace", index=False)
    
    try:
        orders = pd.read_sql_query("SELECT * FROM orders", conn)
    except Exception as e:
        logger.error(f"Error loading orders: {e}")
        orders = pd.DataFrame(columns=["معرف الطلب", "التاريخ", "المنتجات", "الإجمالي"])
        orders.to_sql("orders", conn, if_exists="replace", index=False)
    
    try:
        expenses = pd.read_sql_query("SELECT * FROM expenses", conn)
    except Exception as e:
        logger.error(f"Error loading expenses: {e}")
        expenses = pd.DataFrame(columns=["معرف المصروف", "التاريخ", "المبلغ", "التعليق"])
        expenses.to_sql("expenses", conn, if_exists="replace", index=False)
    
    conn.close()
    return products, orders, expenses

def save_data(products, orders, expenses):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    try:
        products.to_sql("products", conn, if_exists="replace", index=False)
        orders.to_sql("orders", conn, if_exists="replace", index=False)
        expenses.to_sql("expenses", conn, if_exists="replace", index=False)
        conn.commit()
        logger.info("Data saved successfully")
    except Exception as e:
        st.error(f"خطأ في حفظ البيانات: {str(e)}")
        logger.error(f"Error saving data: {e}")
    finally:
        conn.close()

def reset_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()

# Initialize database if not exists
if not os.path.exists(DB_FILE):
    init_db()

# Load data into session state for real-time updates
if "products" not in st.session_state:
    products, orders, expenses = load_data()
    st.session_state["products"] = products
    st.session_state["orders"] = orders
    st.session_state["expenses"] = expenses

# Sidebar menu
with st.sidebar:
    selected = option_menu(
        "القائمة الرئيسية",
        ["الرئيسية", "المنتجات", "الطلبات", "المصروفات", "الاسترداد", "الرؤى والإحصاءيات", "التصدير", "إعادة تعيين"],
        icons=["house", "box", "cart", "cash", "arrow-left", "bar-chart", "download", "arrow-clockwise"],
        menu_icon="shop",
        default_index=0,
    )

# Pages
if selected == "الرئيسية":
    st.header("لوحة التحكم - متجر ستوتا")
    total_income = st.session_state["orders"]["الإجمالي"].sum() if not st.session_state["orders"].empty else 0
    total_expenses = st.session_state["expenses"]["المبلغ"].sum() if not st.session_state["expenses"].empty else 0
    sold_product_cost = 0
    total_products_cost = 0
    if not st.session_state["products"].empty:
        st.session_state["products"]["sold_qty"] = st.session_state["products"]["المخزون"].max() - st.session_state["products"]["المخزون"]
        sold_product_cost = (st.session_state["products"]["السعر الأصلي"] * st.session_state["products"]["sold_qty"]).sum()
        total_products_cost = (st.session_state["products"]["السعر الأصلي"] * st.session_state["products"]["المخزون"]).sum()
    net_profit = total_income - (sold_product_cost + total_expenses)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("إجمالي الدخل", f"{total_income:,.2f} جنية")
    with col2:
        st.metric("تكلفة المنتجات المباعة", f"{sold_product_cost:,.2f} جنية")
    with col3:
        st.metric("المصروفات الإضافية", f"{total_expenses:,.2f} جنية")
    with col4:
        st.metric("صافي الربح", f"{net_profit:,.2f} جنية")
    with col5:
        st.metric("إجمالي تكلفة المنتجات", f"{total_products_cost:,.2f} جنية")

elif selected == "المنتجات":
    st.header("إدارة المنتجات")
    search_term = st.text_input("ابحث عن منتج", "")
    filtered_products = st.session_state["products"][st.session_state["products"]["اسم المنتج"].str.contains(search_term, case=False, na=False)] if search_term else st.session_state["products"]
    
    tab1, tab2 = st.tabs(["إضافة منتج", "تعديل وحذف المنتجات"])
    
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
                elif product_id in st.session_state["products"]["معرف المنتج"].values:
                    st.error("معرف المنتج موجود بالفعل!")
                else:
                    try:
                        new_product = pd.DataFrame({
                            "معرف المنتج": [product_id],
                            "اسم المنتج": [product_name],
                            "السعر الأصلي": [original_price],
                            "سعر البيع": [selling_price],
                            "المخزون": [stock]
                        })
                        st.session_state["products"] = pd.concat([st.session_state["products"].drop(columns=["sold_qty"], errors="ignore"), new_product], ignore_index=True)
                        save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                        st.success("تمت إضافة المنتج بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ أثناء إضافة المنتج: {str(e)}")
                        logger.error(f"Error adding product: {e}")
    
    with tab2:
        if not filtered_products.empty:
            st.dataframe(filtered_products.drop(columns=["sold_qty"], errors="ignore"))
            product_to_modify = st.selectbox("اختر المنتج للتعديل أو الحذف", filtered_products["معرف المنتج"])
            product_data = st.session_state["products"][st.session_state["products"]["معرف المنتج"] == product_to_modify].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                with st.form("edit_product"):
                    new_name = st.text_input("اسم المنتج", value=product_data["اسم المنتج"])
                    new_original = st.number_input("السعر الأصلي", value=float(product_data["السعر الأصلي"]))
                    new_selling = st.number_input("سعر البيع", value=float(product_data["سعر البيع"]))
                    new_stock = st.number_input("المخزون", value=int(product_data["المخزون"]))
                    
                    if st.form_submit_button("حفظ التعديلات"):
                        try:
                            st.session_state["products"].loc[st.session_state["products"]["معرف المنتج"] == product_to_modify, ["معرف المنتج", "اسم المنتج", "السعر الأصلي", "سعر البيع", "المخزون"]] = [
                                product_to_modify, new_name, new_original, new_selling, new_stock
                            ]
                            save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                            st.success("تم تعديل المنتج بنجاح!")
                        except Exception as e:
                            st.error(f"خطأ أثناء تعديل المنتج: {str(e)}")
                            logger.error(f"Error editing product: {e}")
            
            with col2:
                with st.form("delete_product"):
                    if st.form_submit_button("حذف المنتج"):
                        try:
                            st.session_state["products"] = st.session_state["products"][st.session_state["products"]["معرف المنتج"] != product_to_modify].reset_index(drop=True)
                            save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                            st.success("تم حذف المنتج بنجاح!")
                        except Exception as e:
                            st.error(f"خطأ أثناء حذف المنتج: {str(e)}")
                            logger.error(f"Error deleting product: {e}")

elif selected == "الطلبات":
    st.header("إدارة الطلبات")
    
    tab1, tab2 = st.tabs(["طلب جديد", "تعديل وحذف الطلبات"])
    
    with tab1:
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        st.write("المنتجات المتاحة:")
        available_products = st.session_state["products"].drop(columns=["sold_qty"], errors="ignore")
        st.dataframe(available_products[["اسم المنتج", "المخزون", "سعر البيع"]])
        
        with st.form("new_order"):
            selected_products = st.multiselect("اختر المنتجات", st.session_state["products"]["اسم المنتج"])
            quantities = {}
            total_preview = 0
            if selected_products:
                st.write("معاينة الطلب:")
                for prod in selected_products:
                    qty = st.number_input(f"الكمية لـ {prod}", min_value=1, step=1, key=f"new_{prod}_{order_id}")
                    quantities[prod] = qty
                    price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                    total_preview += price * qty
                st.write(f"الإجمالي المتوقع: {total_preview:,.2f} جنية")
            
            if st.form_submit_button("إنشاء الطلب"):
                if not selected_products:
                    st.error("يرجى اختيار منتج واحد على الأقل!")
                else:
                    try:
                        total = 0
                        order_details = []
                        for prod in selected_products:
                            price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                            qty = quantities[prod]
                            current_stock = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["المخزون"].iloc[0]
                            if qty > current_stock:
                                st.error(f"الكمية المطلوبة لـ {prod} ({qty}) أكبر من المخزون ({current_stock})!")
                                break
                            total += price * qty
                            order_details.append(f"{prod}: {qty}")
                            st.session_state["products"].loc[st.session_state["products"]["اسم المنتج"] == prod, "المخزون"] -= qty
                        else:
                            new_order = pd.DataFrame({
                                "معرف الطلب": [order_id],
                                "التاريخ": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                "المنتجات": [" | ".join(order_details)],
                                "الإجمالي": [total]
                            })
                            st.session_state["orders"] = pd.concat([st.session_state["orders"], new_order], ignore_index=True)
                            save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                            st.success("تم إنشاء الطلب بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ أثناء إنشاء الطلب: {str(e)}")
                        logger.error(f"Error creating order: {e}")
    
    with tab2:
        if not st.session_state["orders"].empty:
            st.dataframe(st.session_state["orders"])
            order_to_modify = st.selectbox("اختر الطلب للتعديل أو الحذف", st.session_state["orders"]["معرف الطلب"])
            order_data = st.session_state["orders"][st.session_state["orders"]["معرف الطلب"] == order_to_modify].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                with st.form("edit_order"):
                    st.write("المنتجات الحالية:", order_data["المنتجات"])
                    selected_products = st.multiselect("تعديل المنتجات", st.session_state["products"]["اسم المنتج"],
                                                     default=[p.split(":")[0].strip() for p in order_data["المنتجات"].split(" | ")])
                    quantities = {}
                    total_preview = 0
                    if selected_products:
                        for prod in selected_products:
                            default_qty = next((int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ") if p.startswith(prod)), 1)
                            qty = st.number_input(f"الكمية لـ {prod}", min_value=1, step=1, value=default_qty, key=f"edit_{prod}_{order_to_modify}")
                            quantities[prod] = qty
                            price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                            total_preview += price * qty
                        st.write(f"الإجمالي الجديد المتوقع: {total_preview:,.2f} جنية")
                    
                    if st.form_submit_button("حفظ التعديلات"):
                        try:
                            old_items = {p.split(":")[0].strip(): int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ")}
                            for prod, qty in old_items.items():
                                if prod in st.session_state["products"]["اسم المنتج"].values:
                                    st.session_state["products"].loc[st.session_state["products"]["اسم المنتج"] == prod, "المخزون"] += qty
                            
                            total = 0
                            order_details = []
                            for prod in selected_products:
                                price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                                qty = quantities[prod]
                                current_stock = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["المخزون"].iloc[0]
                                if qty > current_stock:
                                    st.error(f"الكمية المطلوبة لـ {prod} ({qty}) أكبر من المخزون ({current_stock})!")
                                    break
                                total += price * qty
                                order_details.append(f"{prod}: {qty}")
                                st.session_state["products"].loc[st.session_state["products"]["اسم المنتج"] == prod, "المخزون"] -= qty
                            else:
                                st.session_state["orders"].loc[st.session_state["orders"]["معرف الطلب"] == order_to_modify, ["معرف الطلب", "التاريخ", "المنتجات", "الإجمالي"]] = [
                                    order_to_modify, order_data["التاريخ"], " | ".join(order_details), total
                                ]
                                save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                                st.success("تم تعديل الطلب بنجاح!")
                        except Exception as e:
                            st.error(f"خطأ أثناء تعديل الطلب: {str(e)}")
                            logger.error(f"Error editing order: {e}")
            
            with col2:
                with st.form("delete_order"):
                    if st.form_submit_button("حذف الطلب"):
                        try:
                            old_items = {p.split(":")[0].strip(): int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ")}
                            for prod, qty in old_items.items():
                                if prod in st.session_state["products"]["اسم المنتج"].values:
                                    st.session_state["products"].loc[st.session_state["products"]["اسم المنتج"] == prod, "المخزون"] += qty
                            st.session_state["orders"] = st.session_state["orders"][st.session_state["orders"]["معرف الطلب"] != order_to_modify].reset_index(drop=True)
                            save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                            st.success("تم حذف الطلب بنجاح!")
                        except Exception as e:
                            st.error(f"خطأ أثناء حذف الطلب: {str(e)}")
                            logger.error(f"Error deleting order: {e}")

elif selected == "المصروفات":
    st.header("إدارة المصروفات")
    
    with st.form("add_expense"):
        amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
        comment = st.text_input("التعليق (مثل: نقل، كهرباء)")
        if st.form_submit_button("إضافة مصروف"):
            if not comment or amount <= 0:
                st.error("يرجى إدخال مبلغ صالح وتعليق!")
            else:
                try:
                    new_expense = pd.DataFrame({
                        "معرف المصروف": [None],
                        "التاريخ": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                        "المبلغ": [amount],
                        "التعليق": [comment]
                    })
                    st.session_state["expenses"] = pd.concat([st.session_state["expenses"], new_expense], ignore_index=True)
                    save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                    st.success("تمت إضافة المصروف بنجاح!")
                except Exception as e:
                    st.error(f"خطأ أثناء إضافة المصروف: {str(e)}")
                    logger.error(f"Error adding expense: {e}")
    
    if not st.session_state["expenses"].empty:
        st.dataframe(st.session_state["expenses"])
        expense_to_modify = st.selectbox("اختر المصروف للتعديل أو الحذف", st.session_state["expenses"]["معرف المصروف"])
        expense_data = st.session_state["expenses"][st.session_state["expenses"]["معرف المصروف"] == expense_to_modify].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            with st.form("edit_expense"):
                new_amount = st.number_input("المبلغ", min_value=0.0, step=0.01, value=float(expense_data["المبلغ"]))
                new_comment = st.text_input("التعليق", value=expense_data["التعليق"])
                if st.form_submit_button("حفظ التعديلات"):
                    try:
                        st.session_state["expenses"].loc[st.session_state["expenses"]["معرف المصروف"] == expense_to_modify, ["التاريخ", "المبلغ", "التعليق"]] = [
                            expense_data["التاريخ"], new_amount, new_comment
                        ]
                        save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                        st.success("تم تعديل المصروف بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ أثناء تعديل المصروف: {str(e)}")
                        logger.error(f"Error editing expense: {e}")
        
        with col2:
            with st.form("delete_expense"):
                if st.form_submit_button("حذف المصروف"):
                    try:
                        st.session_state["expenses"] = st.session_state["expenses"][st.session_state["expenses"]["معرف المصروف"] != expense_to_modify].reset_index(drop=True)
                        save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                        st.success("تم حذف المصروف بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ أثناء حذف المصروف: {str(e)}")
                        logger.error(f"Error deleting expense: {e}")

elif selected == "الاسترداد":
    st.header("استرداد المنتجات")
    
    if not st.session_state["orders"].empty:
        order_to_refund = st.selectbox("اختر الطلب للاسترداد", st.session_state["orders"]["معرف الطلب"])
        order_data = st.session_state["orders"][st.session_state["orders"]["معرف الطلب"] == order_to_refund].iloc[0]
        
        with st.form("refund_order"):
            st.write("المنتجات في الطلب:", order_data["المنتجات"])
            refund_items = {}
            for item in order_data["المنتجات"].split(" | "):
                prod, qty = item.split(":")
                refund_qty = st.number_input(f"كمية الاسترداد لـ {prod}", min_value=0, max_value=int(qty), step=1, key=f"refund_{prod}_{order_to_refund}")
                if refund_qty > 0:
                    refund_items[prod.strip()] = refund_qty
            
            if st.form_submit_button("تنفيذ الاسترداد"):
                if not refund_items:
                    st.error("يرجى اختيار كمية للاسترداد!")
                else:
                    try:
                        total_refunded = 0
                        old_items = {p.split(":")[0].strip(): int(p.split(":")[1]) for p in order_data["المنتجات"].split(" | ")}
                        new_details = []
                        for prod, old_qty in old_items.items():
                            refund_qty = refund_items.get(prod, 0)
                            if refund_qty > 0:
                                price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == prod]["سعر البيع"].iloc[0]
                                total_refunded += price * refund_qty
                                st.session_state["products"].loc[st.session_state["products"]["اسم المنتج"] == prod, "المخزون"] += refund_qty
                            remaining_qty = old_qty - refund_qty
                            if remaining_qty > 0:
                                new_details.append(f"{prod}: {remaining_qty}")
                        
                        if new_details:
                            st.session_state["orders"].loc[st.session_state["orders"]["معرف الطلب"] == order_to_refund, "المنتجات"] = " | ".join(new_details)
                            st.session_state["orders"].loc[st.session_state["orders"]["معرف الطلب"] == order_to_refund, "الإجمالي"] -= total_refunded
                        else:
                            st.session_state["orders"] = st.session_state["orders"][st.session_state["orders"]["معرف الطلب"] != order_to_refund].reset_index(drop=True)
                        
                        save_data(st.session_state["products"], st.session_state["orders"], st.session_state["expenses"])
                        st.success(f"تم استرداد {total_refunded:,.2f} جنية بنجاح!")
                    except Exception as e:
                        st.error(f"خطأ أثناء الاسترداد: {str(e)}")
                        logger.error(f"Error processing refund: {e}")
    else:
        st.info("لا توجد طلبات للاسترداد.")

elif selected == "الرؤى والإحصاءيات":
    st.header("الرؤى والإحصاءيات")
    
    if not st.session_state["orders"].empty and not st.session_state["products"].empty:
        total_income = st.session_state["orders"]["الإجمالي"].sum()
        total_expenses = st.session_state["expenses"]["المبلغ"].sum() if not st.session_state["expenses"].empty else 0
        st.session_state["products"]["sold_qty"] = st.session_state["products"]["المخزون"].max() - st.session_state["products"]["المخزون"]
        sold_product_cost = (st.session_state["products"]["السعر الأصلي"] * st.session_state["products"]["sold_qty"]).sum()
        total_products_cost = (st.session_state["products"]["السعر الأصلي"] * st.session_state["products"]["المخزون"]).sum()
        net_profit = total_income - (sold_product_cost + total_expenses)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("إجمالي الدخل", f"{total_income:,.2f} جنية")
        with col2:
            st.metric("تكلفة المنتجات المباعة", f"{sold_product_cost:,.2f} جنية")
        with col3:
            st.metric("المصروفات الإضافية", f"{total_expenses:,.2f} جنية")
        with col4:
            st.metric("صافي الربح", f"{net_profit:,.2f} جنية")
        with col5:
            st.metric("إجمالي تكلفة المنتجات", f"{total_products_cost:,.2f} جنية")
        
        st.subheader("تحليل المبيعات")
        st.session_state["orders"]["التاريخ"] = pd.to_datetime(st.session_state["orders"]["التاريخ"])
        daily_sales = st.session_state["orders"].groupby(st.session_state["orders"]["التاريخ"].dt.date)["الإجمالي"].sum().reset_index()
        fig1 = px.line(daily_sales, x="التاريخ", y="الإجمالي", title="المبيعات اليومية",
                      labels={"التاريخ": "التاريخ", "الإجمالي": "المبيعات (جنية)"})
        st.plotly_chart(fig1)
        
        product_sales = pd.DataFrame()
        for _, row in st.session_state["orders"].iterrows():
            items = row["المنتجات"].split(" | ")
            for item in items:
                name, qty = item.split(":")
                price = st.session_state["products"][st.session_state["products"]["اسم المنتج"] == name.strip()]["سعر البيع"].iloc[0]
                product_sales = pd.concat([product_sales, pd.DataFrame({
                    "المنتج": [name.strip()],
                    "الكمية": [int(qty)],
                    "الإجمالي": [price * int(qty)]
                })], ignore_index=True)
        fig2 = px.bar(product_sales.groupby("المنتج").sum().reset_index(), 
                     x="المنتج", y="الإجمالي", title="المبيعات حسب المنتج",
                     labels={"المنتج": "اسم المنتج", "الإجمالي": "الإيرادات (جنية)"},
                     color="الكمية")
        st.plotly_chart(fig2)

elif selected == "التصدير":
    st.header("تصدير البيانات")
    
    export_type = st.selectbox("اختر نوع البيانات", ["المنتجات", "الطلبات", "المصروفات", "الكل"])
    if st.button("تصدير إلى CSV"):
        try:
            if export_type == "المنتجات":
                st.session_state["products"].drop(columns=["sold_qty"], errors="ignore").to_csv("exported_products.csv", index=False)
                st.download_button("تحميل", data=open("exported_products.csv", "rb"), file_name="exported_products.csv")
            elif export_type == "الطلبات":
                st.session_state["orders"].to_csv("exported_orders.csv", index=False)
                st.download_button("تحميل", data=open("exported_orders.csv", "rb"), file_name="exported_orders.csv")
            elif export_type == "المصروفات":
                st.session_state["expenses"].to_csv("exported_expenses.csv", index=False)
                st.download_button("تحميل", data=open("exported_expenses.csv", "rb"), file_name="exported_expenses.csv")
            else:
                with pd.ExcelWriter("stota_full_data.xlsx") as writer:
                    st.session_state["products"].drop(columns=["sold_qty"], errors="ignore").to_excel(writer, sheet_name="المنتجات", index=False)
                    st.session_state["orders"].to_excel(writer, sheet_name="الطلبات", index=False)
                    st.session_state["expenses"].to_excel(writer, sheet_name="المصروفات", index=False)
                st.download_button("تحميل", data=open("stota_full_data.xlsx", "rb"), file_name="stota_full_data.xlsx")
            st.success("تم التصدير بنجاح!")
        except Exception as e:
            st.error(f"خطأ في التصدير: {str(e)}")
            logger.error(f"Error exporting data: {e}")
    
    st.subheader("إدارة قاعدة البيانات")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("تحميل قاعدة البيانات"):
            try:
                with open(DB_FILE, "rb") as f:
                    st.download_button("تنزيل stota_store.db", f, file_name="stota_store.db")
                st.success("تم تحضير قاعدة البيانات!")
            except Exception as e:
                st.error(f"خطأ في التحميل: {str(e)}")
                logger.error(f"Error downloading database: {e}")
    with col2:
        uploaded_file = st.file_uploader("رفع قاعدة بيانات", type=["db"])
        if uploaded_file:
            try:
                with open(DB_FILE, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state["products"], st.session_state["orders"], st.session_state["expenses"] = load_data()
                st.success("تم رفع قاعدة البيانات وتحديث البيانات!")
            except Exception as e:
                st.error(f"خطأ في الرفع: {str(e)}")
                logger.error(f"Error uploading database: {e}")

elif selected == "إعادة تعيين":
    st.header("إعادة تعيين التطبيق")
    st.warning("سيؤدي هذا إلى حذف جميع البيانات (المنتجات، الطلبات، المصروفات). هل أنت متأكد؟")
    if st.button("إعادة تعيين الكل"):
        try:
            reset_db()
            st.session_state["products"], st.session_state["orders"], st.session_state["expenses"] = load_data()
            st.success("تم إعادة تعيين التطبيق بنجاح!")
        except Exception as e:
            st.error(f"خطأ أثناء إعادة التعيين: {str(e)}")
            logger.error(f"Error resetting app: {e}")
