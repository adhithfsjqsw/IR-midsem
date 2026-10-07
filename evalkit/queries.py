"""Pilot query set.  DEV queries were used to set the fixed weights; TEST queries were never used for tuning.
All are phrased as propositions so that support = favours the proposition, oppose = limits / negates it."""

DEV = {
    "D1": "Can an employer terminate a probationary employee without prior notice?",
    "D2": "Can anticipatory bail be granted to an accused in a serious offence?",
    "D3": "Can delay in filing an appeal be condoned by the court?",
}
TEST = {
    "T1": "Is a complaint under Section 138 of the Negotiable Instruments Act maintainable without a statutory demand notice?",
    "T2": "Can a High Court quash an FIR in exercise of inherent powers under Section 482 of the Code of Criminal Procedure?",
    "T3": "Can a court set aside an arbitral award under Section 34 on the ground of erroneous interpretation of the contract?",
    "T4": "Is a confession made to a police officer admissible in evidence?",
    "T5": "Is circumstantial evidence sufficient to sustain a conviction?",
    "T6": "Is prior sanction required to prosecute a public servant for corruption?",
    "T7": "Is reservation in promotion permissible for scheduled castes and scheduled tribes?",
    "T8": "Can the court enhance compensation for land acquired under the Land Acquisition Act?",
    "T9": "Can a person claim title by adverse possession against the true owner?",
    "T10": "Is a divorced wife entitled to maintenance under Section 125 of the Code of Criminal Procedure?",
    "T11": "Can a landlord evict a tenant on the ground of bona fide personal requirement?",
    "T12": "Is an insurance company liable to pay compensation when the driver did not hold a valid licence?",
}
ALL = {**DEV, **TEST}

# FRESH: written after the system was frozen (v2); never used for tuning or inspection before pooling.
FRESH = {
    "F1": "Can bail be granted to an accused in an offence under the Narcotic Drugs and Psychotropic Substances Act?",
    "F2": "Is an oral agreement for sale of immovable property enforceable by a suit for specific performance?",
    "F3": "Can an FIR be registered for a cognizable offence without a preliminary inquiry?",
    "F4": "Is an ex parte decree liable to be set aside under Order IX Rule 13 of the Code of Civil Procedure?",
    "F5": "Can a dying declaration alone form the basis of conviction?",
    "F6": "Is a daughter entitled to a share in coparcenary property under the Hindu Succession Act?",
    "F7": "Can a government employee be dismissed from service without holding a departmental inquiry?",
    "F8": "Can interest be awarded on compensation under the Motor Vehicles Act?",
}
ALL = {**DEV, **TEST, **FRESH}
