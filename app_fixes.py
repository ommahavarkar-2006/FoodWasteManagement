# Complete fixed app.py with all corrections
# This will be merged with the existing app.py

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

@app.route('/ngo/<int:ngo_id>/donations')
def ngo_donations_dashboard(ngo_id):
    # Check if NGO is logged in and matches the requested NGO
    if 'ngo_id' not in session or session['ngo_id'] != ngo_id:
        flash('Access denied. Please login as the NGO.', 'warning')
        return redirect(url_for('ngo_login'))
    
    try:
        cur = mysql.connection.cursor()
        
        # Get NGO details
        cur.execute("SELECT name, description FROM ngos WHERE id = %s", (ngo_id,))
        ngo = cur.fetchone()
        
        if not ngo:
            flash('NGO not found!', 'danger')
            return redirect(url_for('ngo_login'))
        
        # Get donations made to this NGO
        cur.execute("""
            SELECT d.*, u.name as donor_name, u.email as donor_email
            FROM donations d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.ngo_id = %s
            ORDER BY d.created_at DESC
        """, (ngo_id,))
        donations = cur.fetchall()
        
        # Get statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_donations,
                COALESCE(SUM(amount), 0) as total_amount,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_donations,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_donations
            FROM donations 
            WHERE ngo_id = %s
        """, (ngo_id,))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('ngo_donations_dashboard.html', ngo=ngo, donations=donations, stats=stats)
        
    except Exception as e:
        flash(f'Error loading NGO dashboard: {str(e)}', 'danger')
        return redirect(url_for('ngo_login'))