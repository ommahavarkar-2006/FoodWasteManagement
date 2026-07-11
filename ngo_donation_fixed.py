@app.route('/ngo-donation', methods=['GET', 'POST'])
def ngo_donation():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        ngo_id = request.form.get('ngo_id')
        ngo_name = request.form.get('ngo_name')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        message = request.form.get('message')
        
        # Validate required fields
        if not all([ngo_id, ngo_name, amount, payment_method]):
            flash('All required fields must be filled!', 'danger')
            return redirect(url_for('ngo_donation'))
        
        try:
            amount = float(amount)
            if amount < 10:
                flash('Minimum donation amount is ₹10!', 'danger')
                return redirect(url_for('ngo_donation'))
        except ValueError:
            flash('Please enter a valid amount!', 'danger')
            return redirect(url_for('ngo_donation'))
        
        try:
            cur = mysql.connection.cursor()
            
            # Insert donation record with completed status
            cur.execute("""
                INSERT INTO donations 
                (user_id, ngo_id, amount, payment_method, status, message)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session['user_id'], ngo_id, amount, payment_method, 'completed', message))
            
            donation_id = cur.lastrowid
            mysql.connection.commit()
            cur.close()
            
            flash(f'Donation of ₹{amount} to {ngo_name} recorded successfully! Status: Completed', 'success')
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            flash(f'Error processing donation: {str(e)}', 'danger')
            return redirect(url_for('ngo_donation'))
    
    # GET request - show NGO selection page
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, address, description FROM ngos WHERE is_verified = TRUE ORDER BY name")
        ngos = cur.fetchall()
        cur.close()
        
        return render_template('ngo_donation.html', ngos=ngos)
        
    except Exception as e:
        flash(f'Error loading NGOs: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))