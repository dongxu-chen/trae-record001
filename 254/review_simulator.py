import pandas as pd
import numpy as np
import os
from train_model import load_model, preprocess_data
from predict import create_sample_claim, create_suspicious_claim
from risk_analysis import analyze_single_claim, generate_tiered_decision
from generate_data import generate_phone_number, generate_address, generate_hospital, generate_bank_account, generate_name


class ClaimReviewSimulator:
    def __init__(self):
        print("="*70)
        print("INSURANCE CLAIM FRAUD REVIEW SIMULATOR")
        print("保险理赔欺诈审核模拟系统")
        print("="*70)
        
        self.model, self.preprocessor, self.feature_names = load_model()
        
        import shap
        self.explainer = shap.TreeExplainer(self.model)
    
    def input_claim_manually(self):
        print("\n" + "="*70)
        print("MANUAL CLAIM INPUT - 手动输入理赔信息")
        print("="*70)
        print("Please enter the following claim information (press Enter for default):")
        print()
        
        claim = {}
        
        print("--- 被保人信息 ---")
        claim['name'] = input("姓名 (默认: 随机生成): ").strip() or generate_name()
        claim['phone'] = input("手机号 (默认: 随机生成): ").strip() or generate_phone_number()
        claim['address'] = input("地址 (默认: 随机生成): ").strip() or generate_address()
        claim['bank_account'] = input("银行账号 (默认: 随机生成): ").strip() or generate_bank_account()
        claim['age'] = int(input("年龄 (默认: 35): ") or 35)
        claim['gender'] = input("性别 (男/女, 默认: 男): ").strip() or '男'
        claim['occupation'] = input("职业 (默认: 办公室职员): ").strip() or '办公室职员'
        claim['region'] = input("地区 (默认: 华东): ").strip() or '华东'
        claim['marital_status'] = input("婚姻状况 (默认: 已婚): ").strip() or '已婚'
        claim['driving_years'] = int(input("驾龄 (默认: 10): ") or 10)
        claim['annual_income'] = int(input("年收入 (默认: 180000): ") or 180000)
        
        print("\n--- 事故信息 ---")
        claim['accident_type'] = input("事故类型 (默认: 追尾事故): ").strip() or '追尾事故'
        claim['accident_season'] = input("事故季节 (春/夏/秋/冬, 默认: 夏): ").strip() or '夏'
        claim['accident_time'] = input("事故时间 (早高峰/日间/晚高峰/夜间, 默认: 日间): ").strip() or '日间'
        claim['accident_weather'] = input("天气 (晴/雨/雪/雾/冰雹, 默认: 晴): ").strip() or '晴'
        
        print("\n--- 车辆信息 ---")
        claim['vehicle_age'] = int(input("车龄 (默认: 3): ") or 3)
        claim['vehicle_type'] = input("车辆类型 (默认: 轿车): ").strip() or '轿车'
        claim['vehicle_value'] = int(input("车辆价值 (默认: 250000): ") or 250000)
        
        print("\n--- 保险信息 ---")
        claim['coverage_type'] = input("险种 (默认: 商业险-全险): ").strip() or '商业险-全险'
        claim['policy_premium'] = int(input("保费 (默认: 8000): ") or 8000)
        claim['policy_duration'] = int(input("保险期限(年) (默认: 1): ") or 1)
        
        print("\n--- 历史理赔 ---")
        claim['past_claims_count'] = int(input("历史理赔次数 (默认: 0): ") or 0)
        claim['past_claims_total'] = int(input("历史理赔总金额 (默认: 0): ") or 0)
        claim['past_fraud_count'] = int(input("历史欺诈次数 (默认: 0): ") or 0)
        
        print("\n--- 理赔明细 ---")
        claim['hospital'] = input("就诊医院 (默认: 随机生成): ").strip() or generate_hospital()
        claim['medical_expense'] = int(input("医疗费用 (默认: 3000): ") or 3000)
        claim['vehicle_repair_cost'] = int(input("车辆维修费用 (默认: 12000): ") or 12000)
        claim['third_party_injury'] = int(input("是否有人伤 (0/1, 默认: 0): ") or 0)
        claim['third_party_medical'] = int(input("第三方医疗费用 (默认: 0): ") or 0)
        claim['third_party_property_damage'] = int(input("第三方财产损失 (默认: 2000): ") or 2000)
        claim['total_claim_amount'] = claim['medical_expense'] + claim['vehicle_repair_cost'] + claim['third_party_medical'] + claim['third_party_property_damage']
        claim['deductible'] = int(input("免赔额 (默认: 1000): ") or 1000)
        claim['claim_amount'] = max(0, claim['total_claim_amount'] - claim['deductible'])
        claim['hospital_days'] = int(input("住院天数 (默认: 0): ") or 0)
        claim['disability_level'] = int(input("伤残等级 (0-5, 默认: 0): ") or 0)
        
        print("\n--- 证明材料 ---")
        claim['police_report'] = int(input("是否有警方报告 (0/1, 默认: 1): ") or 1)
        claim['witness_present'] = int(input("是否有目击者 (0/1, 默认: 1): ") or 1)
        claim['photos_provided'] = int(input("是否提供现场照片 (0/1, 默认: 1): ") or 1)
        claim['repair_invoice'] = int(input("是否有维修发票 (0/1, 默认: 1): ") or 1)
        claim['medical_invoice'] = int(input("是否有医疗发票 (0/1, 默认: 1): ") or 1)
        claim['claim_processing_days'] = int(input("理赔处理天数 (默认: 5): ") or 5)
        
        claim['claim_ratio'] = claim['claim_amount'] / claim['policy_premium'] if claim['policy_premium'] > 0 else 0
        claim['expense_to_value_ratio'] = claim['total_claim_amount'] / claim['vehicle_value'] if claim['vehicle_value'] > 0 else 0
        claim['same_day_claim'] = 1 if claim['claim_processing_days'] <= 1 else 0
        claim['high_value_ratio'] = 1 if claim['expense_to_value_ratio'] > 0.5 else 0
        claim['suspicious_time'] = 1 if claim['accident_time'] in ['夜间', '晚高峰'] and claim['accident_weather'] in ['晴', '阴'] else 0
        
        fraud_indicators = 0
        if claim['past_fraud_count'] > 0: fraud_indicators += 1
        if not claim['police_report']: fraud_indicators += 1
        if not claim['witness_present']: fraud_indicators += 1
        if claim['same_day_claim']: fraud_indicators += 1
        if claim['high_value_ratio']: fraud_indicators += 1
        if claim['suspicious_time']: fraud_indicators += 1
        claim['fraud_indicators'] = fraud_indicators
        
        return claim
    
    def review_claim(self, claim_data, claim_id="MANUAL_001"):
        print("\n" + "="*70)
        print(f"CLAIM REVIEW - 理赔审核")
        print(f"Claim ID: {claim_id}")
        print("="*70)
        
        print("\n【理赔信息摘要】")
        print("-"*70)
        print(f"  被保人: {claim_data.get('name', 'N/A')}")
        print(f"  手机号: {claim_data.get('phone', 'N/A')}")
        print(f"  住址: {claim_data.get('address', 'N/A')}")
        print(f"  年龄: {claim_data.get('age', 'N/A')} | 驾龄: {claim_data.get('driving_years', 'N/A')}年")
        print(f"  职业: {claim_data.get('occupation', 'N/A')}")
        print()
        print(f"  事故类型: {claim_data.get('accident_type', 'N/A')}")
        print(f"  事故时间: {claim_data.get('accident_season', 'N/A')} {claim_data.get('accident_time', 'N/A')}")
        print(f"  天气: {claim_data.get('accident_weather', 'N/A')}")
        print()
        print(f"  车辆: {claim_data.get('vehicle_type', 'N/A')} | 车龄: {claim_data.get('vehicle_age', 'N/A')}年 | 价值: ¥{claim_data.get('vehicle_value', 0):,}")
        print(f"  险种: {claim_data.get('coverage_type', 'N/A')} | 保费: ¥{claim_data.get('policy_premium', 0):,}")
        print()
        print(f"  医疗费用: ¥{claim_data.get('medical_expense', 0):,} | 就诊医院: {claim_data.get('hospital', 'N/A')}")
        print(f"  维修费用: ¥{claim_data.get('vehicle_repair_cost', 0):,}")
        print(f"  第三方损失: ¥{claim_data.get('third_party_property_damage', 0):,}")
        print(f"  理赔总金额: ¥{claim_data.get('total_claim_amount', 0):,}")
        print(f"  实际赔付: ¥{claim_data.get('claim_amount', 0):,}")
        print()
        print(f"  警方报告: {'✅ 有' if claim_data.get('police_report') else '❌ 无'}")
        print(f"  现场目击者: {'✅ 有' if claim_data.get('witness_present') else '❌ 无'}")
        print(f"  现场照片: {'✅ 有' if claim_data.get('photos_provided') else '❌ 无'}")
        print(f"  医疗发票: {'✅ 有' if claim_data.get('medical_invoice') else '❌ 无'}")
        print(f"  维修发票: {'✅ 有' if claim_data.get('repair_invoice') else '❌ 无'}")
        print(f"  历史欺诈记录: {claim_data.get('past_fraud_count', 0)}次")
        print(f"  欺诈指标数: {claim_data.get('fraud_indicators', 0)}个")
        
        analysis_result = analyze_single_claim(
            claim_data, self.model, self.preprocessor, 
            self.feature_names, self.explainer, claim_id
        )
        
        workflow = generate_tiered_decision(analysis_result, claim_data)
        
        return {
            'claim_id': claim_id,
            'claim_data': claim_data,
            'analysis_result': analysis_result,
            'workflow': workflow
        }
    
    def run_simulator(self):
        while True:
            print("\n" + "="*70)
            print("SIMULATOR MENU - 模拟菜单")
            print("="*70)
            print("1. Review High Risk Claim (高风险案例)")
            print("2. Review Low Risk Claim (低风险案例)")
            print("3. Input Custom Claim (手动输入)")
            print("4. Batch Review Test Cases (批量测试)")
            print("0. Exit (退出)")
            
            choice = input("\nPlease select an option: ").strip()
            
            if choice == '1':
                print("\n" + "="*70)
                print("REVIEWING HIGH RISK CLAIM")
                print("="*70)
                claim = create_suspicious_claim()
                claim['name'] = generate_name()
                claim['phone'] = generate_phone_number()
                claim['address'] = generate_address()
                claim['bank_account'] = generate_bank_account()
                claim['hospital'] = generate_hospital()
                self.review_claim(claim, claim_id="HIGH_RISK_DEMO")
                
            elif choice == '2':
                print("\n" + "="*70)
                print("REVIEWING LOW RISK CLAIM")
                print("="*70)
                claim = create_sample_claim()
                claim['name'] = generate_name()
                claim['phone'] = generate_phone_number()
                claim['address'] = generate_address()
                claim['bank_account'] = generate_bank_account()
                claim['hospital'] = generate_hospital()
                self.review_claim(claim, claim_id="LOW_RISK_DEMO")
                
            elif choice == '3':
                claim = self.input_claim_manually()
                self.review_claim(claim, claim_id="MANUAL_CLAIM")
                
            elif choice == '4':
                self.batch_review()
                
            elif choice == '0':
                print("\nThank you for using the Claim Review Simulator!")
                break
                
            else:
                print("\nInvalid option. Please try again.")
            
            input("\nPress Enter to continue...")
    
    def batch_review(self):
        print("\n" + "="*70)
        print("BATCH REVIEW - 批量审核测试")
        print("="*70)
        
        test_cases = []
        
        print("\nGenerating 5 test cases...")
        
        for i in range(3):
            claim = create_suspicious_claim()
            claim['name'] = generate_name()
            claim['phone'] = generate_phone_number()
            claim['address'] = generate_address()
            claim['bank_account'] = generate_bank_account()
            claim['hospital'] = generate_hospital()
            test_cases.append((f"TEST_HIGH_{i+1}", claim))
        
        for i in range(2):
            claim = create_sample_claim()
            claim['name'] = generate_name()
            claim['phone'] = generate_phone_number()
            claim['address'] = generate_address()
            claim['bank_account'] = generate_bank_account()
            claim['hospital'] = generate_hospital()
            test_cases.append((f"TEST_LOW_{i+1}", claim))
        
        results = []
        print(f"\nProcessing {len(test_cases)} test cases...")
        
        for claim_id, claim in test_cases:
            X_processed, _, _, _ = preprocess_data(pd.DataFrame([claim]), is_train=False, preprocessor=self.preprocessor)
            fraud_prob = self.model.predict_proba(X_processed)[0, 1]
            
            if fraud_prob >= 0.7:
                risk = "🔴 高"
            elif fraud_prob >= 0.4:
                risk = "🟡 中"
            else:
                risk = "🟢 低"
            
            results.append({
                'Claim ID': claim_id,
                'Type': '欺诈' if 'HIGH' in claim_id else '正常',
                'Fraud Prob': f"{fraud_prob:.2%}",
                'Risk Level': risk,
                'Amount': f"¥{claim['claim_amount']:,}"
            })
        
        results_df = pd.DataFrame(results)
        print(f"\n{'='*70}")
        print("BATCH REVIEW RESULTS")
        print(f"{'='*70}")
        print(results_df.to_string(index=False))
        print(f"{'='*70}")
        
        return results_df


def run_simulator():
    simulator = ClaimReviewSimulator()
    simulator.run_simulator()


if __name__ == '__main__':
    run_simulator()
