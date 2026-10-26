Attribute VB_Name = "Module1"
Option Explicit

Private Const REPORT_SHEET As String = "LAPORAN"
Private Const DATA_SHEET As String = "LAPORAN"
Private Const REF_SHEET As String = "LAPORAN"
Private Const DATA_FIRST_ROW As Long = 40

Private Function DistrictRows() As Variant
    DistrictRows = Array(9, 10, 11, 13, 14, 15, 17, 18, 19, _
                         21, 22, 23, 25, 26, 27, 29, 30, 31, _
                         33, 34, 35)
End Function

Public Sub InitializeUPT()
    On Error GoTo CleanFail
    Application.EnableEvents = False
    Application.ScreenUpdating = False

    RestoreCalculatedFormulas
    Worksheets(REPORT_SHEET).Calculate
    LoadSelectedPeriod

CleanExit:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
CleanFail:
    MsgBox "Data UPT belum dapat dimuat: " & Err.Description, vbExclamation, "Laporan UPT"
    Resume CleanExit
End Sub

Public Sub HandleUPTChange(ByVal Sh As Object, ByVal Target As Object)
    Dim inputArea As Range
    Dim selectorArea As Range
    Dim calculatedArea As Range

    If Sh.Name <> REPORT_SHEET Then Exit Sub

    On Error GoTo CleanFail
    Application.EnableEvents = False
    Application.ScreenUpdating = False

    Set selectorArea = Sh.Range("B2,E2,E3,G2")
    Set inputArea = FrontendInputRange(Sh)
    Set calculatedArea = CalculatedRange(Sh)

    If Not Intersect(Target, selectorArea) Is Nothing Then
        SavePreviousDailyView
        Sh.Calculate
        RestoreCalculatedFormulas
        LoadSelectedPeriod
    ElseIf Not Intersect(Target, inputArea) Is Nothing Then
        If CStr(Sh.Range("B2").Value) = "Harian" Then
            SaveDailyGrid CDate(Sh.Range("B3").Value)
            Sh.Calculate
        Else
            MsgBox "Input langsung hanya dilakukan pada mode Harian. Mode Bulanan adalah rekap otomatis.", _
                   vbInformation, "Laporan UPT"
            LoadSelectedPeriod
        End If
    ElseIf Not Intersect(Target, calculatedArea) Is Nothing Then
        RestoreCalculatedFormulas
        Sh.Calculate
    End If

CleanExit:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
CleanFail:
    MsgBox "Perubahan belum dapat disimpan: " & Err.Description, vbExclamation, "Laporan UPT"
    Resume CleanExit
End Sub

Public Sub SaveUPTBeforeClose()
    On Error GoTo CleanExit
    Application.EnableEvents = False
    SavePreviousDailyView
CleanExit:
    Application.EnableEvents = True
End Sub

Private Sub SavePreviousDailyView()
    Dim refWs As Worksheet
    Dim previousDate As Variant
    Dim previousMode As String

    Set refWs = Worksheets(REF_SHEET)
    previousDate = refWs.Range("V2").Value
    previousMode = CStr(refWs.Range("V3").Value)

    If previousMode = "Harian" And IsDate(previousDate) Then
        SaveDailyGrid CDate(previousDate)
    End If
End Sub

Private Sub LoadSelectedPeriod()
    Dim reportWs As Worksheet
    Dim refWs As Worksheet
    Dim selectedDate As Date
    Dim modeName As String

    Set reportWs = Worksheets(REPORT_SHEET)
    Set refWs = Worksheets(REF_SHEET)

    reportWs.Calculate
    selectedDate = CDate(reportWs.Range("B3").Value)
    modeName = CStr(reportWs.Range("B2").Value)

    ClearFrontendGrid reportWs
    If modeName = "Bulanan" Then
        LoadMonthlyGrid selectedDate
    Else
        LoadDailyGrid selectedDate
    End If

    refWs.Range("V2").Value = selectedDate
    refWs.Range("V2").NumberFormat = "dd mmm yyyy"
    refWs.Range("V3").Value = modeName
    RestoreCalculatedFormulas
    reportWs.Calculate
End Sub

Private Sub SaveDailyGrid(ByVal selectedDate As Date)
    Dim reportWs As Worksheet
    Dim dataWs As Worksheet
    Dim rowsList As Variant
    Dim item As Variant
    Dim reportRow As Long
    Dim dataRow As Long
    Dim districtName As String
    Dim uptName As String
    Dim hasInput As Boolean

    Set reportWs = Worksheets(REPORT_SHEET)
    Set dataWs = Worksheets(DATA_SHEET)
    rowsList = DistrictRows()

    For Each item In rowsList
        reportRow = CLng(item)
        districtName = CStr(reportWs.Cells(reportRow, "A").Value)
        dataRow = FindDataRow(dataWs, selectedDate, districtName)
        hasInput = RowHasInput(reportWs, reportRow)

        If hasInput Then
            If dataRow = 0 Then dataRow = FirstFreeDataRow(dataWs)
            uptName = UPTForReportRow(reportWs, reportRow)

            dataWs.Cells(dataRow, "L").Value = selectedDate
            dataWs.Cells(dataRow, "L").NumberFormat = "dd mmm yyyy"
            dataWs.Cells(dataRow, "M").Value = IndonesianDayName(selectedDate)
            dataWs.Cells(dataRow, "N").Value = uptName
            dataWs.Cells(dataRow, "O").Value = districtName
            dataWs.Cells(dataRow, "P").Value = reportWs.Cells(reportRow, "B").Value
            dataWs.Cells(dataRow, "Q").Value = reportWs.Cells(reportRow, "C").Value
            dataWs.Cells(dataRow, "R").Value = reportWs.Cells(reportRow, "D").Value
            dataWs.Cells(dataRow, "S").Value = reportWs.Cells(reportRow, "E").Value
            dataWs.Cells(dataRow, "T").Value = reportWs.Cells(reportRow, "G").Value
        ElseIf dataRow > 0 Then
            dataWs.Range("L" & dataRow & ":T" & dataRow).ClearContents
        End If
    Next item
End Sub

Private Sub LoadDailyGrid(ByVal selectedDate As Date)
    Dim reportWs As Worksheet
    Dim dataWs As Worksheet
    Dim rowsList As Variant
    Dim item As Variant
    Dim reportRow As Long
    Dim dataRow As Long
    Dim districtName As String

    Set reportWs = Worksheets(REPORT_SHEET)
    Set dataWs = Worksheets(DATA_SHEET)
    rowsList = DistrictRows()

    For Each item In rowsList
        reportRow = CLng(item)
        districtName = CStr(reportWs.Cells(reportRow, "A").Value)
        dataRow = FindDataRow(dataWs, selectedDate, districtName)

        If dataRow > 0 Then
            reportWs.Cells(reportRow, "B").Value = dataWs.Cells(dataRow, "P").Value
            reportWs.Cells(reportRow, "C").Value = dataWs.Cells(dataRow, "Q").Value
            reportWs.Cells(reportRow, "D").Value = dataWs.Cells(dataRow, "R").Value
            reportWs.Cells(reportRow, "E").Value = dataWs.Cells(dataRow, "S").Value
            reportWs.Cells(reportRow, "G").Value = dataWs.Cells(dataRow, "T").Value
        End If
    Next item
End Sub

Private Sub LoadMonthlyGrid(ByVal selectedDate As Date)
    Dim reportWs As Worksheet
    Dim dataWs As Worksheet
    Dim rowsList As Variant
    Dim item As Variant
    Dim reportRow As Long
    Dim dataRow As Long
    Dim lastRow As Long
    Dim districtName As String
    Dim recordDate As Date
    Dim petugas As Double
    Dim targetWP As Double
    Dim sppt As Double
    Dim rupiah As Double
    Dim latestNote As String
    Dim latestNoteDate As Date
    Dim hasData As Boolean

    Set reportWs = Worksheets(REPORT_SHEET)
    Set dataWs = Worksheets(DATA_SHEET)
    rowsList = DistrictRows()
    lastRow = dataWs.Cells(dataWs.Rows.Count, "L").End(xlUp).Row
    If lastRow < DATA_FIRST_ROW Then lastRow = DATA_FIRST_ROW

    For Each item In rowsList
        reportRow = CLng(item)
        districtName = CStr(reportWs.Cells(reportRow, "A").Value)
        petugas = 0
        targetWP = 0
        sppt = 0
        rupiah = 0
        latestNote = ""
        latestNoteDate = 0
        hasData = False

        For dataRow = DATA_FIRST_ROW To lastRow
            If CStr(dataWs.Cells(dataRow, "O").Value) = districtName _
               And IsDate(dataWs.Cells(dataRow, "L").Value) Then
                recordDate = CDate(dataWs.Cells(dataRow, "L").Value)
                If Month(recordDate) = Month(selectedDate) _
                   And Year(recordDate) = Year(selectedDate) Then
                    hasData = True
                    petugas = petugas + NumericValue(dataWs.Cells(dataRow, "P").Value)
                    targetWP = targetWP + NumericValue(dataWs.Cells(dataRow, "Q").Value)
                    sppt = sppt + NumericValue(dataWs.Cells(dataRow, "R").Value)
                    rupiah = rupiah + NumericValue(dataWs.Cells(dataRow, "S").Value)
                    If Len(CStr(dataWs.Cells(dataRow, "T").Value)) > 0 Then
                        If recordDate >= latestNoteDate Then
                            latestNoteDate = recordDate
                            latestNote = CStr(dataWs.Cells(dataRow, "T").Value)
                        End If
                    End If
                End If
            End If
        Next dataRow

        If hasData Then
            reportWs.Cells(reportRow, "B").Value = petugas
            reportWs.Cells(reportRow, "C").Value = targetWP
            reportWs.Cells(reportRow, "D").Value = sppt
            reportWs.Cells(reportRow, "E").Value = rupiah
            reportWs.Cells(reportRow, "G").Value = latestNote
        End If
    Next item
End Sub

Private Function FindDataRow(ByVal dataWs As Worksheet, _
                             ByVal selectedDate As Date, _
                             ByVal districtName As String) As Long
    Dim rowNumber As Long
    Dim lastRow As Long

    lastRow = dataWs.Cells(dataWs.Rows.Count, "L").End(xlUp).Row
    If lastRow < DATA_FIRST_ROW Then
        FindDataRow = 0
        Exit Function
    End If

    For rowNumber = DATA_FIRST_ROW To lastRow
        If IsDate(dataWs.Cells(rowNumber, "L").Value) Then
            If CLng(CDate(dataWs.Cells(rowNumber, "L").Value)) = CLng(selectedDate) _
               And CStr(dataWs.Cells(rowNumber, "O").Value) = districtName Then
                FindDataRow = rowNumber
                Exit Function
            End If
        End If
    Next rowNumber

    FindDataRow = 0
End Function

Private Function FirstFreeDataRow(ByVal dataWs As Worksheet) As Long
    Dim rowNumber As Long
    Dim lastRow As Long

    lastRow = dataWs.Cells(dataWs.Rows.Count, "L").End(xlUp).Row
    If lastRow < DATA_FIRST_ROW Then
        FirstFreeDataRow = DATA_FIRST_ROW
        Exit Function
    End If

    For rowNumber = DATA_FIRST_ROW To lastRow
        If Len(CStr(dataWs.Cells(rowNumber, "L").Value)) = 0 Then
            FirstFreeDataRow = rowNumber
            Exit Function
        End If
    Next rowNumber

    FirstFreeDataRow = lastRow + 1
End Function

Private Function RowHasInput(ByVal reportWs As Worksheet, ByVal reportRow As Long) As Boolean
    RowHasInput = (Len(CStr(reportWs.Cells(reportRow, "B").Value)) > 0 _
                Or Len(CStr(reportWs.Cells(reportRow, "C").Value)) > 0 _
                Or Len(CStr(reportWs.Cells(reportRow, "D").Value)) > 0 _
                Or Len(CStr(reportWs.Cells(reportRow, "E").Value)) > 0 _
                Or Len(CStr(reportWs.Cells(reportRow, "G").Value)) > 0)
End Function

Private Function UPTForReportRow(ByVal reportWs As Worksheet, ByVal reportRow As Long) As String
    Dim rowNumber As Long
    For rowNumber = reportRow To 8 Step -1
        If Left$(CStr(reportWs.Cells(rowNumber, "A").Value), 3) = "UPT" Then
            UPTForReportRow = CStr(reportWs.Cells(rowNumber, "A").Value)
            Exit Function
        End If
    Next rowNumber
    UPTForReportRow = ""
End Function

Private Function IndonesianDayName(ByVal selectedDate As Date) As String
    IndonesianDayName = Choose(Weekday(selectedDate), "Minggu", "Senin", "Selasa", _
                               "Rabu", "Kamis", "Jumat", "Sabtu")
End Function

Private Function NumericValue(ByVal inputValue As Variant) As Double
    If IsNumeric(inputValue) Then
        NumericValue = CDbl(inputValue)
    Else
        NumericValue = 0
    End If
End Function

Private Sub ClearFrontendGrid(ByVal reportWs As Worksheet)
    Dim rowsList As Variant
    Dim item As Variant
    rowsList = DistrictRows()
    For Each item In rowsList
        reportWs.Range("B" & CLng(item) & ":E" & CLng(item)).ClearContents
        reportWs.Cells(CLng(item), "G").ClearContents
    Next item
End Sub

Private Function FrontendInputRange(ByVal reportWs As Worksheet) As Range
    Set FrontendInputRange = Union( _
        reportWs.Range("B9:E11"), reportWs.Range("G9:G11"), _
        reportWs.Range("B13:E15"), reportWs.Range("G13:G15"), _
        reportWs.Range("B17:E19"), reportWs.Range("G17:G19"), _
        reportWs.Range("B21:E23"), reportWs.Range("G21:G23"), _
        reportWs.Range("B25:E27"), reportWs.Range("G25:G27"), _
        reportWs.Range("B29:E31"), reportWs.Range("G29:G31"), _
        reportWs.Range("B33:E35"), reportWs.Range("G33:G35"))
End Function

Private Function CalculatedRange(ByVal reportWs As Worksheet) As Range
    Set CalculatedRange = Union( _
        reportWs.Range("B8:G8"), reportWs.Range("B12:G12"), _
        reportWs.Range("B16:G16"), reportWs.Range("B20:G20"), _
        reportWs.Range("B24:G24"), reportWs.Range("B28:G28"), _
        reportWs.Range("B32:G32"), reportWs.Range("B36:G36"), _
        reportWs.Range("F9:F11"), reportWs.Range("F13:F15"), _
        reportWs.Range("F17:F19"), reportWs.Range("F21:F23"), _
        reportWs.Range("F25:F27"), reportWs.Range("F29:F31"), _
        reportWs.Range("F33:F35"))
End Function

Private Sub RestoreCalculatedFormulas()
    Dim reportWs As Worksheet
    Dim rowsList As Variant
    Dim item As Variant
    Dim uptList As Variant
    Dim uptItem As Variant
    Dim uptRow As Long
    Dim firstChild As Long

    Set reportWs = Worksheets(REPORT_SHEET)
    rowsList = DistrictRows()
    For Each item In rowsList
        reportWs.Cells(CLng(item), "F").Formula = "=IFERROR(D" & CLng(item) & "/C" & CLng(item) & ",0)"
    Next item

    uptList = Array(8, 12, 16, 20, 24, 28, 32)
    For Each uptItem In uptList
        uptRow = CLng(uptItem)
        firstChild = uptRow + 1
        reportWs.Cells(uptRow, "B").Formula = "=SUM(B" & firstChild & ":B" & firstChild + 2 & ")"
        reportWs.Cells(uptRow, "C").Formula = "=SUM(C" & firstChild & ":C" & firstChild + 2 & ")"
        reportWs.Cells(uptRow, "D").Formula = "=SUM(D" & firstChild & ":D" & firstChild + 2 & ")"
        reportWs.Cells(uptRow, "E").Formula = "=SUM(E" & firstChild & ":E" & firstChild + 2 & ")"
        reportWs.Cells(uptRow, "F").Formula = "=IFERROR(D" & uptRow & "/C" & uptRow & ",0)"
        reportWs.Cells(uptRow, "G").Formula = "=""Total ""&A" & uptRow
    Next uptItem

    reportWs.Range("B36").Formula = "=SUM(B8,B12,B16,B20,B24,B28,B32)"
    reportWs.Range("C36").Formula = "=SUM(C8,C12,C16,C20,C24,C28,C32)"
    reportWs.Range("D36").Formula = "=SUM(D8,D12,D16,D20,D24,D28,D32)"
    reportWs.Range("E36").Formula = "=SUM(E8,E12,E16,E20,E24,E28,E32)"
    reportWs.Range("F36").Formula = "=IFERROR(D36/C36,0)"
    reportWs.Range("G36").Formula = "=IF(B2=""Harian"",""Total harian"",""Total bulanan"")"
End Sub
