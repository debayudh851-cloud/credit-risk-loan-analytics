import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((ROOT/'artifacts/dashboard_applications.csv').exists(),'Run pipeline first')
class DashboardTests(unittest.TestCase):
    def app(self):
        at=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=45).run()
        self.assertFalse(at.exception,[str(e.value) for e in at.exception])
        return at
    def test_default_dashboard_kpis(self):
        at=self.app()
        self.assertEqual(at.metric[0].value,'7,500')
        self.assertEqual(at.metric[1].value,'46.4%')
        self.assertEqual(at.metric[2].value,'23.4%')
        self.assertEqual(len(at.tabs),3)
    def test_region_risk_and_loan_filters(self):
        at=self.app()
        at.sidebar.multiselect[0].set_value(['Maharashtra'])
        at.sidebar.multiselect[1].set_value(['Personal'])
        at.sidebar.multiselect[3].set_value(['High Risk'])
        at.run()
        self.assertFalse(at.exception,[str(e.value) for e in at.exception])
        if at.dataframe:
            watch=at.dataframe[0].value
            self.assertTrue(watch.state.eq('Maharashtra').all())
            self.assertTrue(watch.risk_category.eq('High Risk').all())
    def test_application_selection(self):
        at=self.app()
        at.selectbox[-1].select_index(3).run()
        self.assertFalse(at.exception)
        self.assertTrue(any(m.label=='Risk score' for m in at.metric))

if __name__=='__main__':unittest.main()
